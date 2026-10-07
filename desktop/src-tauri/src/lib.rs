use serde::Serialize;
use std::{
    env, fs::{self, File}, io::{Read, Write}, net::TcpListener,
    path::{Path, PathBuf}, process::{Child, Command, Stdio},
    sync::Mutex, thread, time::{Duration, Instant},
};
use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct ToolStatus { pub name: String, pub installed: bool }

const TOOLS: [&str; 5] = ["codex", "ollama", "opencode", "gemini", "git"];

fn executable_exists_in(name: &str, search_path: &std::ffi::OsStr) -> bool {
    let path = Path::new(name);
    if path.components().count() > 1 { return path.is_file(); }
    env::split_paths(search_path).any(|dir| {
        if dir.join(name).is_file() { return true; }
        #[cfg(windows)]
        { [".exe", ".cmd", ".bat"].iter().any(|ext| dir.join(format!("{name}{ext}")).is_file()) }
        #[cfg(not(windows))]
        { false }
    })
}

fn detect_tools_in(search_path: &std::ffi::OsStr) -> Vec<ToolStatus> {
    TOOLS.iter().map(|name| ToolStatus { name: (*name).to_string(), installed: executable_exists_in(name, search_path) }).collect()
}

fn navigation_is_allowed(url: &tauri::Url, port: u16) -> bool {
    if url.scheme() == "tauri" { return true; }
    if matches!(url.scheme(), "http" | "https") && url.host_str() == Some("tauri.localhost") { return true; }
    url.scheme() == "http" && url.host_str() == Some("127.0.0.1") && url.port() == Some(port)
}

fn api_initialization_script(port: u16, token: &str) -> String {
    let token = serde_json::to_string(token).unwrap_or_else(|_| "\"\"".into());
    format!("window.__GLACIER_API__ = \"http://127.0.0.1:{port}\"; window.__GLACIER_TOKEN__ = {token};")
}

/// The per-install engine token (GLACIER_HOME/.engine-token), shared with the engine and command-line tools.
/// Created here on first launch with 32 random bytes; owner-only on Unix, user-profile ACL on Windows.
fn engine_token(data_dir: &Path) -> Result<String, String> {
    let path = data_dir.join(".engine-token");
    if let Ok(existing) = fs::read_to_string(&path) {
        let existing = existing.trim().to_string();
        if !existing.is_empty() {
            return Ok(existing);
        }
    }
    let mut bytes = [0u8; 32];
    getrandom::fill(&mut bytes).map_err(|e| e.to_string())?;
    let token: String = bytes.iter().map(|b| format!("{b:02x}")).collect();
    let mut options = fs::OpenOptions::new();
    options.write(true).create(true).truncate(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options.open(&path).map_err(|e| e.to_string())?;
    std::io::Write::write_all(&mut file, token.as_bytes()).map_err(|e| e.to_string())?;
    Ok(token)
}

#[tauri::command]
fn available_tools() -> Vec<ToolStatus> { detect_tools_in(&env::var_os("PATH").unwrap_or_default()) }

#[derive(Default)]
struct BackendProcess(Mutex<Option<Child>>);

fn free_listener() -> TcpListener { TcpListener::bind(("127.0.0.1", 0)).expect("reserve local port") }

fn resource_path(app: &tauri::AppHandle, relative: &str) -> PathBuf {
    app.path().resource_dir().unwrap_or_else(|_| PathBuf::from(".")).join(relative)
}

fn runtime_platform() -> &'static str {
    if cfg!(target_os = "windows") { "x86_64-pc-windows-msvc" }
    else if cfg!(target_os = "macos") { "aarch64-apple-darwin" }
    else { "x86_64-unknown-linux-gnu" }
}

fn launch_backend(app: &tauri::AppHandle, port: u16) -> Result<(Child, PathBuf), String> {
    let config_path = resource_path(app, "sidecar.json");
    let config: serde_json::Value = fs::read_to_string(config_path).ok()
        .and_then(|s| serde_json::from_str(&s).ok()).unwrap_or_default();
    let relative_python = config.get("runtime_by_platform").and_then(|x| x.get(runtime_platform()))
        .and_then(|x| x.as_str()).ok_or_else(|| "The bundled Python runtime is not configured".to_string())?;
    let python = resource_path(app, relative_python);
    let backend_dir = resource_path(app, "backend");
    let low_resource = config.get("low_resource").and_then(|x| x.as_bool()).unwrap_or(false);
    let data_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    fs::create_dir_all(&data_dir).map_err(|e| e.to_string())?;
    let log_path = data_dir.join("backend.log");
    let log_file = File::create(&log_path).map_err(|e| e.to_string())?;
    let log_stderr = log_file.try_clone().map_err(|e| e.to_string())?;
    let port_text = port.to_string();
    if !python.is_file() {
        return Err(format!("The bundled Python runtime is missing at {}", python.display()));
    }
    let mut command = Command::new(python);
    command.current_dir(backend_dir).args(["-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", &port_text])
        .env("GLACIER_HOME", data_dir).stdin(Stdio::null()).stdout(Stdio::from(log_file)).stderr(Stdio::from(log_stderr));
    if low_resource {
        if let Some(values) = config.get("low_resource_env").and_then(|x| x.as_object()) {
            for (key, value) in values {
                if let Some(value) = value.as_str() { command.env(key, value); }
                else if let Some(value) = value.as_number() { command.env(key, value.to_string()); }
            }
        }
    }
    command.spawn().map(|child| (child, log_path.clone()))
        .map_err(|e| format!("Could not start the bundled Python runtime: {e}; log: {}", log_path.display()))
}

fn backend_ready(port: u16) -> bool {
    let addr = format!("127.0.0.1:{port}");
    let Ok(mut stream) = std::net::TcpStream::connect(&addr) else { return false; };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
    let request = format!("GET /api/node-types HTTP/1.0\r\nHost: {addr}\r\n\r\n");
    if stream.write_all(request.as_bytes()).is_err() { return false; }
    let mut response = String::new();
    stream.read_to_string(&mut response).is_ok() && (response.starts_with("HTTP/1.1 200") || response.starts_with("HTTP/1.0 200"))
}

fn show_start_error(app: &tauri::AppHandle, log_path: &Path) {
    let message = format!("Glacier's engine didn't start. Details are in {}", log_path.display());
    let Ok(message) = serde_json::to_string(&message) else { return; };
    if let Some(window) = app.get_webview_window("main") {
        let script = format!("(()=>{{let tries=0;const show=()=>{{if(typeof window.showStartupError==='function')window.showStartupError({message});else if(tries++<100)setTimeout(show,50)}};show()}})()");
        let _ = window.eval(&script);
    }
}

pub fn run() {
    let app = tauri::Builder::default()
        .manage(BackendProcess::default())
        .invoke_handler(tauri::generate_handler![available_tools])
        .setup(|app| {
            let port = free_listener().local_addr()?.port();
            let data_dir = app.path().app_data_dir()?;
            fs::create_dir_all(&data_dir)?;
            let token = engine_token(&data_dir).map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
            let window = WebviewWindowBuilder::new(app.handle(), "main", WebviewUrl::App("first-run/index.html".into()))
                .title("Welcome to Glacier").inner_size(1280.0, 820.0)
                .initialization_script(api_initialization_script(port, &token))
                .on_navigation(move |url| navigation_is_allowed(url, port))
                .build()?;
            match launch_backend(&app.handle(), port) {
                Ok((child, log_path)) => {
                    let state = app.state::<BackendProcess>();
                    *state.0.lock().expect("backend state") = Some(child);
                    let handle = app.handle().clone();
                    thread::spawn(move || {
                        let start = Instant::now();
                        while start.elapsed() < Duration::from_secs(45) {
                            if backend_ready(port) {
                                if let Some(window) = handle.get_webview_window("main") {
                                    let _ = window.set_title("Glacier");
                                    if let Ok(mut url) = window.url() {
                                        url.set_path("/index.html");
                                        let _ = window.navigate(url);
                                    }
                                }
                                return;
                            }
                            let exited = handle.state::<BackendProcess>().0.lock().ok()
                                .and_then(|mut child| child.as_mut().and_then(|c| c.try_wait().ok().flatten())).is_some();
                            if exited { show_start_error(&handle, &log_path); return; }
                            thread::sleep(Duration::from_millis(250));
                        }
                        show_start_error(&handle, &log_path);
                    });
                }
                Err(details) => {
                    let log_path = details.rsplit_once("; log: ").map(|(_, p)| PathBuf::from(p))
                        .unwrap_or_else(|| app.path().app_data_dir().unwrap_or_default().join("backend.log"));
                    show_start_error(&app.handle(), &log_path);
                }
            }
            let _ = window;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Glacier desktop");
    app.run(|app, event| {
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            if let Some(state) = app.try_state::<BackendProcess>() {
                if let Ok(mut guard) = state.0.lock() {
                    if let Some(child) = guard.as_mut() { let _ = child.kill(); let _ = child.wait(); }
                    *guard = None;
                }
            }
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bundled_screen_navigation_stays_local_and_allows_the_backend() {
        let port = 43127;
        assert!(navigation_is_allowed(&"tauri://localhost/index.html".parse().unwrap(), port));
        assert!(navigation_is_allowed(&"http://tauri.localhost/index.html".parse().unwrap(), port));
        assert!(navigation_is_allowed(&"https://tauri.localhost/index.html".parse().unwrap(), port));
        assert!(navigation_is_allowed(&format!("http://127.0.0.1:{port}/api/node-types").parse().unwrap(), port));
        assert!(!navigation_is_allowed(&"https://example.com/".parse().unwrap(), port));
        assert!(!navigation_is_allowed(&format!("http://127.0.0.1:{}/", port + 1).parse().unwrap(), port));
    }

    #[test]
    fn api_address_is_injected_into_bundled_pages() {
        assert_eq!(api_initialization_script(43127, "abc"), "window.__GLACIER_API__ = \"http://127.0.0.1:43127\"; window.__GLACIER_TOKEN__ = \"abc\";");
    }

    #[test]
    fn engine_token_is_created_once_and_reused() {
        let dir = std::env::temp_dir().join(format!("glacier-token-test-{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let first = engine_token(&dir).unwrap();
        assert_eq!(first.len(), 64);
        assert_eq!(engine_token(&dir).unwrap(), first);
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(fs::metadata(dir.join(".engine-token")).unwrap().permissions().mode() & 0o777, 0o600);
        }
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn runtime_platform_uses_a_supported_distribution_folder() {
        assert!(matches!(runtime_platform(), "x86_64-unknown-linux-gnu" | "aarch64-apple-darwin" | "x86_64-pc-windows-msvc"));
    }

    #[test]
    fn detects_installed_tools() {
        let root = std::env::temp_dir().join(format!("glacier-tool-detection-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(&root).unwrap();
        fs::write(root.join("git"), "fake executable").unwrap();
        let tools = detect_tools_in(root.as_os_str());
        assert_eq!(tools.iter().map(|tool| tool.name.as_str()).collect::<Vec<_>>(), vec!["codex", "ollama", "opencode", "gemini", "git"]);
        assert!(!tools.iter().find(|tool| tool.name == "codex").unwrap().installed);
        assert!(tools.iter().find(|tool| tool.name == "git").unwrap().installed);
        let _ = fs::remove_dir_all(root);
    }
}
