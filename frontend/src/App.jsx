import { useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./index.css";

const API = "http://127.0.0.1:8000";

function getId(node) {
  return String(node?.id ?? "");
}

function getLabel(node) {
  return node?.label ?? node?.name ?? node?.id ?? "Unknown";
}

function App() {
  const [twin, setTwin] = useState(null);
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [online, setOnline] = useState(false);

  useEffect(() => {
    loadTwin();
  }, []);

  async function loadTwin() {
    try {
      const response = await fetch(`${API}/twin`);

      if (!response.ok) {
        throw new Error("Backend unavailable");
      }

      const data = await response.json();

      setTwin(data);
      setOnline(true);

      if (data.nodes?.length) {
        setSource(getId(data.nodes[0]));
        setTarget(getId(data.nodes[data.nodes.length - 1]));
      }
    } catch (err) {
      console.error(err);
      setOnline(false);
      setError("Unable to connect to ShadowTwin backend.");
    }
  }

  const nodes = useMemo(
    () => Array.isArray(twin?.nodes) ? twin.nodes : [],
    [twin]
  );

  const edges = useMemo(
    () => Array.isArray(twin?.edges) ? twin.edges : [],
    [twin]
  );

  const controls = useMemo(
    () => Array.isArray(twin?.controls) ? twin.controls : [],
    [twin]
  );

  function getNode(id) {
    return nodes.find(
      (node) => getId(node) === String(id)
    );
  }

  function getNodeName(id) {
    return getLabel(getNode(id));
  }

  /*
   * Build a set containing every edge that belongs
   * to the first discovered attack path.
   */
  const highlightedEdges = useMemo(() => {
    const set = new Set();

    const firstPath = result?.paths?.[0];

    if (!firstPath?.edges) {
      return set;
    }

    firstPath.edges.forEach((edge) => {
      set.add(
        `${edge.source}->${edge.target}`
      );
    });

    return set;
  }, [result]);

  const graphNodes = useMemo(() => {
    const columns = 4;

    return nodes.map((node, index) => {
      const criticality = Number(
        node?.criticality ?? 1
      );

      const isSource =
        result &&
        String(result.source) === getId(node);

      const isTarget =
        result &&
        String(result.target) === getId(node);

      return {
        id: getId(node),

        position: {
          x: (index % columns) * 260,
          y: Math.floor(index / columns) * 150,
        },

        data: {
          label:
            `${getLabel(node)}\n` +
            `${node?.type ?? "asset"} · ` +
            `${node?.zone ?? "unknown"}`,
        },

        style: {
          width: 190,
          padding: 12,

          background: isTarget
            ? "#e9e9e5"
            : "#ffffff",

          border:
            isSource || isTarget
              ? "3px solid #222"
              : criticality >= 4
                ? "2px solid #555"
                : "1px solid #999",

          borderRadius: 3,

          color: "#222",

          fontSize: 10,

          lineHeight: 1.4,

          whiteSpace: "pre-line",

          textAlign: "left",

          boxShadow:
            isSource || isTarget
              ? "0 0 0 3px #d8d8d3"
              : "none",
        },
      };
    });
  }, [nodes, result]);

  const graphEdges = useMemo(() => {
    return edges
      .filter(
        (edge) =>
          edge?.source &&
          edge?.target
      )
      .map((edge, index) => {
        const key =
          `${edge.source}->${edge.target}`;

        const highlighted =
          highlightedEdges.has(key);

        return {
          id:
            String(
              edge.id ??
              `edge-${index}`
            ),

          source: String(edge.source),

          target: String(edge.target),

          label: edge.relation ?? "",

          animated: highlighted,

          style: {
            stroke: highlighted
              ? "#111"
              : "#999",

            strokeWidth:
              highlighted
                ? 4
                : 1.3,
          },

          labelStyle: {
            fill: highlighted
              ? "#111"
              : "#666",

            fontSize:
              highlighted
                ? 9
                : 8,

            fontWeight:
              highlighted
                ? 700
                : 400,
          },

          labelBgStyle: {
            fill: "#f1f1ee",
            fillOpacity: 0.95,
          },
        };
      });
  }, [edges, highlightedEdges]);

  async function runSimulation() {
    if (!source || !target) {
      setError(
        "Select an attack source and target."
      );
      return;
    }

    if (source === target) {
      setError(
        "Source and target must be different."
      );
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const url =
        `${API}/simulate` +
        `?source=${encodeURIComponent(source)}` +
        `&target=${encodeURIComponent(target)}`;

      const response = await fetch(url);

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data?.detail ??
          "Simulation failed."
        );
      }

      setResult(data);
    } catch (err) {
      console.error(err);

      setError(
        err.message ??
        "Simulation failed."
      );
    } finally {
      setLoading(false);
    }
  }

  if (!twin) {
    return (
      <div className="loading-screen">
        <h1>SHADOWTWIN</h1>

        <p>
          Connecting to digital twin...
        </p>

        {error && (
          <div className="error">
            {error}
          </div>
        )}
      </div>
    );
  }

  const riskScore =
    Number(result?.risk?.score ?? 0);

  const riskLevel =
    result?.risk?.level ??
    "NOT ANALYSED";

  const attackPaths =
    Array.isArray(result?.paths)
      ? result.paths
      : [];

  const mitre =
    Array.isArray(result?.mitre)
      ? result.mitre
      : [];

  const recommendations =
    Array.isArray(
      result?.recommendations
    )
      ? result.recommendations
      : [];

  return (
    <div className="app">

      {/* HEADER */}

      <header className="header">

        <div>
          <h1>SHADOWTWIN</h1>

          <p>
            Cyber Attack Simulation & Defence
          </p>
        </div>

        <div className="status">

          <span
            className={
              online
                ? "online-dot"
                : "offline-dot"
            }
          />

          {online
            ? "SYSTEM ONLINE"
            : "BACKEND OFFLINE"}

        </div>

      </header>


      <main>

        {/* ORGANISATION */}

        <section className="hero">

          <small>
            ORGANISATION
          </small>

          <h2>
            {twin.org ?? "Acme FinServ"}
          </h2>

          <p>
            Live digital twin security environment
          </p>

        </section>


        {/* METRICS */}

        <section className="metrics">

          <div>
            <small>ASSETS</small>
            <strong>{nodes.length}</strong>
          </div>

          <div>
            <small>CONNECTIONS</small>
            <strong>{edges.length}</strong>
          </div>

          <div>
            <small>DEFENCE CONTROLS</small>
            <strong>{controls.length}</strong>
          </div>

        </section>


        {/* NETWORK */}

        <section className="graph-card">

          <div className="card-header">

            <div>
              <small>
                LIVE TOPOLOGY
              </small>

              <h2>
                Organisation Network
              </h2>
            </div>

            <span className="count">
              {nodes.length} nodes ·{" "}
              {edges.length} edges
            </span>

          </div>

          {result && (
            <div className="graph-banner">
              <strong>
                DISCOVERED ATTACK PATH
              </strong>

              <span>
                {getNodeName(result.source)}
                {" → "}
                {getNodeName(result.target)}
              </span>
            </div>
          )}

          <div className="graph">

            <ReactFlow
              nodes={graphNodes}
              edges={graphEdges}
              fitView
              fitViewOptions={{
                padding: 0.2,
              }}
              nodesDraggable
              nodesConnectable={false}
              elementsSelectable
            >

              <Background
                gap={24}
                size={1}
              />

              <Controls />

              <MiniMap />

            </ReactFlow>

          </div>

        </section>


        {/* SIMULATION */}

        <section className="workspace">

          <div className="card">

            <div className="card-header">

              <div>
                <small>ANALYSIS</small>

                <h2>
                  Attack Simulation
                </h2>
              </div>

            </div>

            <div className="form">

              <label>
                ATTACK SOURCE
              </label>

              <select
                value={source}
                onChange={(event) =>
                  setSource(
                    event.target.value
                  )
                }
              >

                {nodes.map((node) => (
                  <option
                    key={getId(node)}
                    value={getId(node)}
                  >
                    {getLabel(node)}
                  </option>
                ))}

              </select>


              <label>
                TARGET ASSET
              </label>

              <select
                value={target}
                onChange={(event) =>
                  setTarget(
                    event.target.value
                  )
                }
              >

                {nodes.map((node) => (
                  <option
                    key={getId(node)}
                    value={getId(node)}
                  >
                    {getLabel(node)}
                  </option>
                ))}

              </select>


              <button
                onClick={runSimulation}
                disabled={loading}
              >

                {loading
                  ? "ANALYSING..."
                  : "RUN SIMULATION"}

              </button>

            </div>

          </div>


          {/* SUMMARY */}

          <div className="card">

            <div className="card-header">

              <div>
                <small>RESULT</small>

                <h2>
                  Simulation Summary
                </h2>
              </div>

            </div>


            {!result ? (

              <div className="empty-result">

                <strong>
                  Ready for analysis
                </strong>

                <p>
                  Select a source and critical
                  asset, then run the simulation.
                </p>

              </div>

            ) : (

              <div className="result-box">

                <div className="result-stat">
                  <span>PATHS FOUND</span>
                  <strong>
                    {result.path_count}
                  </strong>
                </div>

                <div className="result-stat">
                  <span>RISK</span>
                  <strong>
                    {riskLevel}
                  </strong>
                </div>

                <div className="result-stat">
                  <span>SCORE</span>
                  <strong>
                    {riskScore}/100
                  </strong>
                </div>

                <div className="result-stat">
                  <span>TARGET</span>
                  <strong>
                    {getNodeName(result.target)}
                  </strong>
                </div>

              </div>

            )}

          </div>

        </section>


        {/* RISK */}

        {result && (

          <section className="risk-panel">

            <div className="risk-main">

              <div>

                <small>
                  THREAT EXPOSURE
                </small>

                <h2>
                  {riskLevel}
                </h2>

                <p>
                  {result.analysis?.explanation}
                </p>

              </div>

              <div className="score">

                <strong>
                  {riskScore}
                </strong>

                <span>
                  / 100
                </span>

              </div>

            </div>


            <div className="risk-stats">

              <div>
                <small>
                  REACHABLE PATHS
                </small>

                <strong>
                  {result.path_count}
                </strong>
              </div>

              <div>
                <small>
                  TARGET CRITICALITY
                </small>

                <strong>
                  {result.analysis
                    ?.target_criticality ?? "—"}
                </strong>
              </div>

              <div>
                <small>
                  AVG. DIFFICULTY
                </small>

                <strong>
                  {result.analysis
                    ?.average_difficulty ?? "—"}
                </strong>
              </div>

              <div>
                <small>
                  TECHNIQUES
                </small>

                <strong>
                  {result.analysis
                    ?.unique_techniques ?? 0}
                </strong>
              </div>

            </div>

          </section>

        )}


        {/* MITRE */}

        {result && (

          <section className="card intelligence">

            <div className="card-header">

              <div>
                <small>
                  ATTACK INTELLIGENCE
                </small>

                <h2>
                  MITRE ATT&CK Techniques
                </h2>
              </div>

              <span className="count">
                {mitre.length} mapped
              </span>

            </div>


            <div className="mitre-grid">

              {mitre.map((technique) => (

                <div
                  className="mitre-card"
                  key={technique.id}
                >

                  <div className="mitre-id">
                    {technique.id}
                  </div>

                  <h3>
                    {technique.name}
                  </h3>

                  <span className="tactic">
                    {technique.tactic}
                  </span>

                  <p>
                    {technique.description}
                  </p>

                </div>

              ))}

            </div>

          </section>

        )}


        {/* ATTACK PATHS */}

        {result && (

          <section className="card attack">

            <div className="card-header">

              <div>
                <small>TRACE</small>

                <h2>
                  Discovered Attack Paths
                </h2>
              </div>

              <span className="count">
                {attackPaths.length} paths
              </span>

            </div>


            {attackPaths.map(
              (path, index) => (

                <div
                  className="path-row"
                  key={index}
                >

                  <div className="path-number">
                    PATH{" "}
                    {String(index + 1)
                      .padStart(2, "0")}
                  </div>


                  <div className="path-chain">

                    {path.nodes.map(
                      (id, nodeIndex) => (

                        <div
                          className="path-step"
                          key={
                            `${id}-${nodeIndex}`
                          }
                        >

                          <div className="path-node">

                            <b>
                              {getNodeName(id)}
                            </b>

                            <span>
                              {getNode(id)?.type ??
                                "asset"}
                            </span>

                          </div>

                          {nodeIndex <
                            path.nodes.length - 1 && (

                            <span className="arrow">
                              →
                            </span>

                          )}

                        </div>

                      )
                    )}

                  </div>


                  <div className="path-techniques">

                    {path.edges.map(
                      (edge, edgeIndex) => (

                        <span
                          key={edgeIndex}
                        >

                          {edge.technique}
                          {" · "}
                          {edge.technique_name}

                        </span>

                      )
                    )}

                  </div>

                </div>

              )
            )}

          </section>

        )}


        {/* DEFENCE */}

        {result && (

          <section className="card defence">

            <div className="card-header">

              <div>
                <small>DEFENCE</small>

                <h2>
                  Recommended Security Controls
                </h2>
              </div>

              <span className="count">
                {recommendations.length} controls
              </span>

            </div>


            <div className="defence-list">

              {recommendations.map(
                (recommendation) => (

                  <div
                    className="defence-item"
                    key={recommendation.id}
                  >

                    <div className="check">
                      ✓
                    </div>

                    <div>

                      <h3>
                        {recommendation.label}
                      </h3>

                      <p>
                        {recommendation.reason}
                      </p>

                    </div>

                  </div>

                )
              )}

            </div>

          </section>

        )}


        {error && (
          <div className="error">
            {error}
          </div>
        )}

      </main>


      <footer>
        SHADOWTWIN · Evidence-driven cyber risk analysis
      </footer>

    </div>
  );
}

export default App;