use serde::Serialize;
use std::{env, fs, net::TcpListener, path::{Path, PathBuf}, process::{Child, Command, Stdio}, thread, time::{Duration, Instant}};
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct ToolStatus {
    pub name: String,
    pub installed: bool,
}

const TOOLS: [&str; 5] = ["codex", "ollama", "opencode", "gemini", "git"];

fn executable_exists_in(name: &str, search_path: &std::ffi::OsStr) -> bool {
    let path = Path::new(name);
    if path.components().count() > 1 {
        return path.is_file();
    }
    env::split_paths(search_path)
        .any(|dir| {
            let candidate = dir.join(name);
            if candidate.is_file() { return true; }
            #[cfg(windows)]
            {
                [".exe", ".cmd", ".bat"].iter().any(|ext| dir.join(format!("{name}{ext}")).is_file())
            }
            #[cfg(not(windows))]
            { false }
        })
}

fn detect_tools() -> Vec<ToolStatus> {
    let search_path = env::var_os("PATH").unwrap_or_default();
    detect_tools_in(&search_path)
}

fn detect_tools_in(search_path: &std::ffi::OsStr) -> Vec<ToolStatus> {
    TOOLS.iter().map(|name| ToolStatus { name: (*name).to_string(), installed: executable_exists_in(name, search_path) }).collect()
}

#[tauri::command]
fn available_tools() -> Vec<ToolStatus> { detect_tools() }

fn free_listener() -> TcpListener {
    TcpListener::bind(("127.0.0.1", 0)).expect("reserve local port")
}

fn resource_path(app: &tauri::AppHandle, relative: &str) -> PathBuf {
    app.path().resource_dir().unwrap_or_else(|_| PathBuf::from("." )).join(relative)
}

fn launch_backend(app: &tauri::AppHandle, port: u16) -> Option<Child> {
    let config_path = resource_path(app, "sidecar.json");
    let config: serde_json::Value = fs::read_to_string(config_path).ok().and_then(|s| serde_json::from_str(&s).ok()).unwrap_or_default();
    let sidecar = config.get("venv_python").and_then(|x| x.as_str()).unwrap_or(".venv/bin/python");
    let python = resource_path(app, sidecar);
    let backend_dir = resource_path(app, "backend");
    let low_resource = config.get("low_resource").and_then(|x| x.as_bool()).unwrap_or(false);
    let data_dir = app.path().app_data_dir().ok()?;
    if fs::create_dir_all(&data_dir).is_err() { return None; }
    let mut command = Command::new(python);
    command.current_dir(backend_dir).args(["-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", &port.to_string()])
        .env("GLACIER_HOME", data_dir).stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null());
    if low_resource {
        if let Some(values) = config.get("low_resource_env").and_then(|x| x.as_object()) {
            for (key, value) in values {
                if let Some(value) = value.as_str() { command.env(key, value); }
                else if let Some(value) = value.as_number() { command.env(key, value.to_string()); }
            }
        }
    }
    command.spawn().ok()
}

fn wait_for_backend(port: u16, timeout: Duration) -> bool {
    let url = format!("http://127.0.0.1:{port}/api/node-types");
    let start = Instant::now();
    while start.elapsed() < timeout {
        if let Ok(response) = ureq_get(&url) {
            if response { return true; }
        }
        thread::sleep(Duration::from_millis(250));
    }
    false
}

fn ureq_get(_url: &str) -> Result<bool, ()> {
    // Use std TCP to keep the native shell dependency-free.
    let addr = _url.trim_start_matches("http://").split('/').next().ok_or(())?;
    let mut stream = std::net::TcpStream::connect(addr).map_err(|_| ())?;
    use std::io::{Read, Write};
    stream.write_all(format!("GET /api/node-types HTTP/1.0\r\nHost: {addr}\r\n\r\n").as_bytes()).map_err(|_| ())?;
    let mut body = String::new();
    stream.read_to_string(&mut body).map_err(|_| ())?;
    Ok(body.starts_with("HTTP/1.1 200") || body.starts_with("HTTP/1.0 200"))
}

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![available_tools])
        .setup(|app| {
            let _window = WebviewWindowBuilder::new(app.handle(), "main", WebviewUrl::App("first-run/index.html".into()))
                .title("Welcome to Glacier").inner_size(1280.0, 820.0).build()?;
            let listener = free_listener();
            let port = listener.local_addr().expect("read local port").port();
            drop(listener);
            let child = launch_backend(&app.handle(), port);
            let handle = app.handle().clone();
            thread::spawn(move || {
                if child.is_some() && wait_for_backend(port, Duration::from_secs(45)) {
                    let url = format!("http://127.0.0.1:{port}");
                    if let Some(window) = handle.get_webview_window("main") {
                        let _ = window.set_title("Glacier");
                        let _ = window.navigate(url.parse().unwrap());
                    }
                }
                if let Some(mut child) = child { let _ = child.wait(); }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Glacier desktop");
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn detects_installed_tools() {
        let root = std::env::temp_dir().join(format!("glacier-tool-detection-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(&root).unwrap();
        let git = root.join("git");
        fs::write(&git, "fake executable").unwrap();
        let tools = detect_tools_in(root.as_os_str());
        assert_eq!(tools.iter().map(|tool| tool.name.as_str()).collect::<Vec<_>>(), vec!["codex", "ollama", "opencode", "gemini", "git"]);
        assert!(!tools.iter().find(|tool| tool.name == "codex").unwrap().installed);
        assert!(tools.iter().find(|tool| tool.name == "git").unwrap().installed);
        let _ = fs::remove_dir_all(root);
    }
}
