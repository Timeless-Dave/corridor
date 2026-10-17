"use client";
import {
  Component,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { Line, OrbitControls, OrthographicCamera } from "@react-three/drei";
import { Vector3, CanvasTexture, SRGBColorSpace } from "three";
import {
  ArrowsOut,
  Graph,
  ListBullets,
  Cube,
  Square,
  Plus,
  Minus,
} from "@phosphor-icons/react";
import { Button } from "./ui/button";
import { exactEdge } from "@/lib/evidence";
import type { Subgraph, GraphNode } from "@/lib/types";
type Position = [number, number, number];
const colors: Record<string, string> = {
  Account: "#64d9c2",
  Device: "#97abd5",
  Phone: "#d8b479",
  Policy: "#b4a6d5",
  Decision: "#bc9e83",
};
function location(id: string, index: number): Position {
  let hash = 0;
  for (const c of id) hash = (hash * 31 + c.charCodeAt(0)) >>> 0;
  const angle = index * 2.39996;
  const radius = 2.5 + Math.sqrt(index) * 0.75;
  return [
    Math.cos(angle) * radius,
    Math.sin(angle) * radius,
    ((hash % 100) / 100 - 0.5) * 3,
  ];
}
class CanvasBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}
function NodeLabel({ id, chosen }: { id: string; chosen: boolean }) {
  const texture = useMemo(() => {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d")!;
    ctx.font = '24px "Geist Mono", monospace';
    canvas.width = Math.ceil(ctx.measureText(id).width) + 24;
    canvas.height = 44;
    ctx.font = '24px "Geist Mono", monospace';
    ctx.fillStyle = "#152124";
    ctx.fillRect(0, 0, canvas.width, 44);
    ctx.strokeStyle = chosen ? "#80e3ca" : "#475f60";
    ctx.strokeRect(1, 1, canvas.width - 2, 42);
    ctx.fillStyle = chosen ? "#80e3ca" : "#c1d7d1";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(id, canvas.width / 2, 22);
    const map = new CanvasTexture(canvas);
    map.colorSpace = SRGBColorSpace;
    return map;
  }, [id, chosen]);
  useEffect(() => () => texture.dispose(), [texture]);
  return (
    <sprite
      position={[0, 0.43, 0]}
      scale={[texture.image.width / 100, 0.44, 1]}
    >
      <spriteMaterial map={texture} transparent depthTest={false} />
    </sprite>
  );
}
function CameraTools({
  fit,
  zoom,
  flat,
  radius,
}: {
  fit: number;
  zoom: number;
  flat: boolean;
  radius: number;
}) {
  const { camera, invalidate, size } = useThree();
  const initialRadius = useRef(radius);
  useEffect(() => {
    const extent = initialRadius.current * 1.25;
    const distance =
      extent / Math.tan(Math.PI / 8) / Math.min(1, size.width / size.height);
    camera.position.set(0, 0, distance * Math.pow(0.85, zoom));
    if ("zoom" in camera && flat) {
      camera.zoom =
        (Math.min(size.width, size.height) / (extent * 2)) *
        Math.pow(1.15, zoom);
      camera.updateProjectionMatrix();
    }
    camera.lookAt(0, 0, 0);
    invalidate();
  }, [camera, fit, zoom, flat, invalidate, size.width, size.height]);
  return null;
}
export default function EvidenceGraph({
  graph,
  cited,
  transfers,
  selected,
  onSelect,
}: {
  graph: Subgraph;
  cited: string[];
  transfers: Set<string>;
  selected: string;
  onSelect: (node: GraphNode) => void;
}) {
  const [list, setList] = useState(false),
    [flat, setFlat] = useState(false),
    [fit, setFit] = useState(0),
    [zoom, setZoom] = useState(0),
    [webgl, setWebgl] = useState(true);
  const positions = useRef(new Map<string, Position>());
  for (const node of graph.nodes)
    if (!positions.current.has(node.id))
      positions.current.set(node.id, location(node.id, positions.current.size));
  useEffect(() => {
    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl2");
      setWebgl(!!gl);
      gl?.getExtension("WEBGL_lose_context")?.loseContext();
    } catch {
      setWebgl(false);
    }
  }, []);
  const citedSet = useMemo(() => new Set(cited), [cited]);
  const pos = (id: string): Position => {
    const p = positions.current.get(id) ?? [0, 0, 0];
    return flat ? [p[0], p[1], 0] : p;
  };
  const listView = (
    <div className="graph-list">
      <p>
        {!webgl
          ? "3D is unavailable. All evidence remains accessible below."
          : "Accessible graph view"}
      </p>
      <h3>Nodes</h3>
      {graph.nodes.map((n) => (
        <button
          className={selected === n.id ? "selected" : ""}
          key={n.id}
          onClick={() => onSelect(n)}
        >
          <span style={{ color: colors[n.labels[0]] ?? "#aaa" }}>●</span>
          <span className="mono">{n.id}</span>
          <small>{n.labels[0]}</small>
        </button>
      ))}
      <h3>Relationships</h3>
      {graph.edges.map((e) => (
        <p className="relationship" key={e.id}>
          <span>{e.source}</span> → <span>{e.target}</span>
          <small>
            {e.type}
            {exactEdge(e, transfers) ? " · cited transfer" : " · context"}
          </small>
        </p>
      ))}
    </div>
  );
  return (
    <section className="graph-panel" aria-label="Evidence graph">
      <div className="panel-heading">
        <div className="inline">
          <Graph size={18} />
          <h2>Connected evidence</h2>
        </div>
        <span>
          {graph.nodes.length} {graph.nodes.length === 1 ? "node" : "nodes"} ·{" "}
          {graph.edges.length} {graph.edges.length === 1 ? "edge" : "edges"}
        </span>
      </div>
      <div className="graph-toolbar">
        <div className="inline">
          <Button
            variant={list ? "ghost" : "secondary"}
            onClick={() => setList(false)}
            aria-label="Show 3D graph"
            disabled={!webgl}
          >
            <Cube size={15} /> Graph
          </Button>
          <Button
            variant={list ? "secondary" : "ghost"}
            onClick={() => setList(true)}
            aria-label="Show accessible graph list"
          >
            <ListBullets size={15} /> List
          </Button>
        </div>
        <div className="inline">
          <Button
            variant="ghost"
            aria-label={flat ? "Use spatial view" : "Use flat view"}
            onClick={() => setFlat(!flat)}
          >
            <Square size={16} />
            {flat ? "Spatial" : "Flat"}
          </Button>
          <Button
            variant="ghost"
            aria-label="Fit graph to view"
            onClick={() => {
              setZoom(0);
              setFit((f) => f + 1);
            }}
          >
            <ArrowsOut size={17} />
          </Button>
        </div>
      </div>
      {!graph.nodes.length ? (
        <div className="graph-empty">
          <Graph size={48} weight="thin" />
          <h3>Evidence builds the picture.</h3>
          <p>
            Cited accounts and relationships appear here as the investigation
            progresses.
          </p>
        </div>
      ) : list || !webgl ? (
        listView
      ) : (
        <CanvasBoundary fallback={listView}>
          <div className="canvas-holder" data-testid="graph-canvas">
            <Canvas
              key={"camera-" + flat + "-" + fit}
              frameloop="demand"
              dpr={[1, 1.5]}
              camera={{ position: [0, 0, 21], fov: 45 }}
              gl={{ antialias: true, alpha: true }}
            >
              <ambientLight intensity={1.3} />
              <directionalLight position={[5, 5, 10]} intensity={2} />
              {flat && (
                <OrthographicCamera
                  makeDefault
                  position={[0, 0, 21]}
                  zoom={42}
                />
              )}
              <CameraTools
                fit={fit}
                zoom={zoom}
                flat={flat}
                radius={Math.max(
                  3,
                  ...Array.from(positions.current.values()).map((p) =>
                    Math.hypot(...p),
                  ),
                )}
              />
              <OrbitControls
                makeDefault
                enableRotate={!flat}
                enableDamping={false}
                minDistance={4}
                maxDistance={60}
              />
              {graph.edges.map((e) => {
                const start = pos(e.source),
                  end = pos(e.target),
                  highlight = exactEdge(e, transfers);
                const a = new Vector3(...start),
                  b = new Vector3(...end),
                  direction = b.clone().sub(a),
                  length = direction.length();
                return (
                  <group key={e.id}>
                    <Line
                      points={[start, end]}
                      color={highlight ? "#80efd3" : "#435256"}
                      lineWidth={highlight ? 2.4 : 1}
                      transparent
                      opacity={highlight ? 1 : 0.55}
                    />
                    {e.type === "SENT" && length > 0.1 && (
                      <arrowHelper
                        args={[
                          direction.normalize(),
                          a,
                          length - 0.22,
                          highlight ? 0x80efd3 : 0x708782,
                          0.24,
                          0.13,
                        ]}
                      />
                    )}
                  </group>
                );
              })}
              {graph.nodes.map((n) => {
                const type = n.labels[0],
                  active = citedSet.has(n.id),
                  chosen = selected === n.id;
                return (
                  <group key={n.id} position={pos(n.id)}>
                    <mesh
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelect(n);
                      }}
                      onPointerOver={() => {
                        document.body.style.cursor = "pointer";
                      }}
                      onPointerOut={() => {
                        document.body.style.cursor = "auto";
                      }}
                      scale={chosen ? 1.4 : active ? 1.15 : 1}
                    >
                      {type === "Account" ? (
                        <sphereGeometry args={[0.19, 20, 16]} />
                      ) : type === "Device" ? (
                        <boxGeometry args={[0.3, 0.3, 0.3]} />
                      ) : type === "Phone" ? (
                        <capsuleGeometry args={[0.1, 0.25, 4, 8]} />
                      ) : (
                        <octahedronGeometry args={[0.25]} />
                      )}
                      <meshStandardMaterial
                        color={colors[type] ?? "#a5b7ba"}
                        emissive={colors[type] ?? "#a5b7ba"}
                        emissiveIntensity={active || chosen ? 0.65 : 0}
                        roughness={0.5}
                        transparent
                        opacity={cited.length && !active && !chosen ? 0.35 : 1}
                      />
                    </mesh>
                    {(chosen || active || graph.nodes.length <= 24) && (
                      <NodeLabel id={n.id} chosen={chosen} />
                    )}
                  </group>
                );
              })}
            </Canvas>
            <div className="zoom-controls">
              <Button
                variant="ghost"
                aria-label="Zoom in"
                onClick={() => setZoom((z) => Math.min(z + 1, 5))}
              >
                <Plus size={16} />
              </Button>
              <Button
                variant="ghost"
                aria-label="Zoom out"
                onClick={() => setZoom((z) => Math.max(z - 1, -4))}
              >
                <Minus size={16} />
              </Button>
            </div>
          </div>
        </CanvasBoundary>
      )}
      <div className="graph-legend">
        {Object.entries(colors).map(([type, color]) => (
          <span key={type}>
            <i style={{ background: color }} />
            {type}
          </span>
        ))}
      </div>
      <div className="graph-caption">
        Teal edges: cited transfers. Muted edges: context. Drag to orbit; scroll
        to zoom.
        {graph.possibly_truncated && (
          <strong> Graph limit reached; some evidence is not displayed.</strong>
        )}
      </div>
    </section>
  );
}
