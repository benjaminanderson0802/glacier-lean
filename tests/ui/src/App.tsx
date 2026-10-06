// Basics test screen: the off-the-shelf pieces Glacier's UI is built from, mounted together. No AI involved.
import { useEffect, useMemo, useRef } from "react";
import { ReactFlow, Handle, Position } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import Editor from "@monaco-editor/react";
import ForceGraph2D from "react-force-graph-2d";

function TerminalNode() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const t = new Terminal({ rows: 4, cols: 32 });
    t.open(ref.current!);
    t.write("worker$ pytest -q\r\n3 passed");
    return () => t.dispose();
  }, []);
  return (
    <div style={{ border: "1px solid #8ab", padding: 4, background: "#fff" }}>
      <Handle type="target" position={Position.Left} />
      <b>Builder worker</b>
      <div ref={ref} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { terminal: TerminalNode };
const nodes = [
  { id: "trigger", position: { x: 0, y: 40 }, data: { label: "Every hour" } },
  { id: "builder", type: "terminal", position: { x: 160, y: 0 }, data: {} },
  { id: "check", position: { x: 480, y: 40 }, data: { label: "Tests pass?" } },
];
const edges = [
  { id: "a", source: "trigger", target: "builder" },
  { id: "b", source: "builder", target: "check" },
  { id: "c", source: "check", target: "builder", animated: true },
];

export default function App() {
  const graph = useMemo(() => ({
    nodes: [{ id: "glacier" }, { id: "engine" }, { id: "builder" }],
    links: [{ source: "glacier", target: "engine" }, { source: "glacier", target: "builder" }],
  }), []);
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
      <div id="canvas" style={{ height: 260 }}><ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView /></div>
      <div id="graph" style={{ height: 260 }}><ForceGraph2D graphData={graph} width={400} height={260} /></div>
      <div id="editor" style={{ height: 200, gridColumn: "1 / 3" }}>
        <Editor defaultLanguage="python" defaultValue={"def test_ok():\n    assert 1 + 1 == 2"} />
      </div>
    </div>
  );
}
