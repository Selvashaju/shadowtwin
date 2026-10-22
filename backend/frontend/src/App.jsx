import { useEffect, useMemo, useState } from "react";
import "./index.css";

const API = "http://127.0.0.1:8000";

function extractNodes(data) {
  if (!data) return [];

  let rawNodes = [];

  if (Array.isArray(data)) {
    rawNodes = data;
  } else if (Array.isArray(data.nodes)) {
    rawNodes = data.nodes;
  } else if (data.graph && Array.isArray(data.graph.nodes)) {
    rawNodes = data.graph.nodes;
  } else if (data.data && Array.isArray(data.data.nodes)) {
    rawNodes = data.data.nodes;
  }

  return rawNodes.map((node, index) => {
    if (typeof node === "string") {
      return {
        id: node,
        label: node,
        type: "asset",
        zone: "",
      };
    }

    return {
      id:
        node.id ??
        node.node_id ??
        node.name ??
        `node-${index + 1}`,

      label:
        node.label ??
        node.name ??
        node.hostname ??
        node.id ??
        node.node_id ??
        `Node ${index + 1}`,

      type:
        node.type ??
        node.asset_type ??
        node.category ??
        "asset",

      zone:
        node.zone ??
        node.network_zone ??
        "",
    };
  });
}

function normalisePaths(rawPaths) {
  if (!Array.isArray(rawPaths)) return [];

  return rawPaths.map((path, index) => {
    if (Array.isArray(path)) {
      return {
        id: index,
        nodes: path,
      };
    }

    if (typeof path === "object" && path !== null) {
      return {
        id: index,
        nodes:
          path.nodes ||
          path.path ||
          path.node_ids ||
          path.steps ||
          [],
      };
    }

    return {
      id: index,
      nodes: [String(path)],
    };
  });
}

function App() {
  const [summary, setSummary] = useState(null);
  const [twin, setTwin] = useState(null);

  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");

  const [paths, setPaths] = useState([]);

  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState("checking");
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setError("");

    try {
      const [summaryResponse, twinResponse] =
        await Promise.all([
          fetch(`${API}/summary`),
          fetch(`${API}/twin`),
        ]);

      if (!summaryResponse.ok) {
        throw new Error("Summary endpoint failed");
      }

      if (!twinResponse.ok) {
        throw new Error("Twin endpoint failed");
      }

      const summaryData =
        await summaryResponse.json();

      const twinData =
        await twinResponse.json();

      setSummary(summaryData);
      setTwin(twinData);
      setBackendStatus("online");

      const loadedNodes =
        extractNodes(twinData);

      if (loadedNodes.length > 0) {
        setSource(loadedNodes[0].id);

        setTarget(
          loadedNodes.length > 1
            ? loadedNodes[loadedNodes.length - 1].id
            : loadedNodes[0].id
        );
      }
    } catch (err) {
      console.error(err);

      setBackendStatus("offline");

      setError(
        "Backend connection unavailable. Make sure FastAPI is running on port 8000."
      );
    }
  }

  const nodes = useMemo(() => {
    return extractNodes(twin);
  }, [twin]);

  async function runSimulation() {
    if (!source || !target) {
      setError(
        "Select an attack source and target."
      );
      return;
    }

    if (source === target) {
      setError(
        "Attack source and target must be different."
      );
      return;
    }

    setLoading(true);
    setError("");
    setPaths([]);

    try {
      const response = await fetch(
        `${API}/simulate?source=${encodeURIComponent(
          source
        )}&target=${encodeURIComponent(target)}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Simulation failed."
        );
      }

      setPaths(
        normalisePaths(
          data.paths ||
          data.attack_paths ||
          data.results ||
          []
        )
      );
    } catch (err) {
      console.error(err);

      setError(
        err.message || "Simulation failed."
      );
    } finally {
      setLoading(false);
    }
  }

  function getNodeLabel(id) {
    const node = nodes.find(
      (item) => String(item.id) === String(id)
    );

    return node?.label || String(id);
  }

  function getNodeType(id) {
    const node = nodes.find(
      (item) => String(item.id) === String(id)
    );

    return node?.type || "asset";
  }

  const risk =
    paths.length === 0
      ? "NOT CALCULATED"
      : paths.length >= 3
      ? "HIGH"
      : paths.length === 2
      ? "MEDIUM"
      : "LOW";

  return (
    <div className="app">

      {/* HEADER */}

      <header className="topbar">

        <div>
          <div className="brand">
            SHADOWTWIN
          </div>

          <div className="tagline">
            Cyber Attack Simulation & Defence
          </div>
        </div>

        <div className="system-status">

          <span
            className={
              backendStatus === "online"
                ? "status-dot online"
                : "status-dot"
            }
          />

          {backendStatus === "online"
            ? "SYSTEM ONLINE"
            : backendStatus === "checking"
            ? "CONNECTING"
            : "BACKEND OFFLINE"}

        </div>

      </header>


      <main>

        {/* OVERVIEW */}

        <section className="overview">

          <div className="organisation-card">

            <span>
              ORGANISATION
            </span>

            <h2>
              {summary?.org ||
                summary?.organization ||
                "Acme FinServ"}
            </h2>

            <p>
              Digital twin security environment
            </p>

          </div>


          <div className="metric">

            <span>ASSETS</span>

            <strong>
              {summary?.nodes ??
                nodes.length ??
                "—"}
            </strong>

          </div>


          <div className="metric">

            <span>CONNECTIONS</span>

            <strong>
              {summary?.edges ?? "—"}
            </strong>

          </div>


          <div className="metric">

            <span>DEFENCE CONTROLS</span>

            <strong>
              {summary?.controls ?? "—"}
            </strong>

          </div>

        </section>


        {/* MAIN AREA */}

        <section className="main-grid">


          {/* NETWORK */}

          <section className="panel">

            <div className="panel-header">

              <div>
                <span>
                  ENVIRONMENT
                </span>

                <h2>
                  Organisation Network
                </h2>
              </div>

              <div className="panel-count">
                {nodes.length} assets
              </div>

            </div>


            <div className="network">

              {nodes.length === 0 ? (

                <div className="empty">

                  <strong>
                    No network data loaded
                  </strong>

                  <p>
                    Check the backend and
                    acme_twin.json.
                  </p>

                </div>

              ) : (

                nodes.map((node, index) => (

                  <div
                    className="network-node"
                    key={`${node.id}-${index}`}
                  >

                    <div className="node-number">
                      {String(index + 1).padStart(
                        2,
                        "0"
                      )}
                    </div>

                    <div className="node-info">

                      <strong>
                        {node.label}
                      </strong>

                      <small>
                        {node.type}
                        {node.zone
                          ? ` · ${node.zone}`
                          : ""}
                      </small>

                    </div>

                    <div className="node-state">
                      ACTIVE
                    </div>

                  </div>

                ))

              )}

            </div>


            <div className="network-footer">

              <span>
                Source: acme_twin.json
              </span>

              <span>
                {backendStatus === "online"
                  ? "Live backend data"
                  : "Waiting for backend"}
              </span>

            </div>

          </section>


          {/* SIMULATION */}

          <section className="panel simulation-panel">

            <div className="panel-header">

              <div>
                <span>
                  ANALYSIS
                </span>

                <h2>
                  Attack Simulation
                </h2>
              </div>

            </div>


            <div className="form">

              <div className="field">

                <label>
                  ATTACK SOURCE
                </label>

                <select
                  value={source}
                  onChange={(event) =>
                    setSource(event.target.value)
                  }
                >

                  <option value="">
                    Select source
                  </option>

                  {nodes.map((node) => (

                    <option
                      key={node.id}
                      value={node.id}
                    >
                      {node.label}
                    </option>

                  ))}

                </select>

              </div>


              <div className="field">

                <label>
                  TARGET ASSET
                </label>

                <select
                  value={target}
                  onChange={(event) =>
                    setTarget(event.target.value)
                  }
                >

                  <option value="">
                    Select target
                  </option>

                  {nodes.map((node) => (

                    <option
                      key={node.id}
                      value={node.id}
                    >
                      {node.label}
                    </option>

                  ))}

                </select>

              </div>


              <button
                className="simulate-button"
                onClick={runSimulation}
                disabled={
                  loading ||
                  backendStatus !== "online"
                }
              >

                {loading
                  ? "RUNNING ANALYSIS..."
                  : "RUN SIMULATION"}

              </button>


              {error && (

                <div className="error-box">
                  {error}
                </div>

              )}

            </div>


            <div className="simulation-summary">

              <div>
                <span>
                  SOURCE
                </span>

                <strong>
                  {source
                    ? getNodeLabel(source)
                    : "—"}
                </strong>
              </div>


              <div>
                <span>
                  TARGET
                </span>

                <strong>
                  {target
                    ? getNodeLabel(target)
                    : "—"}
                </strong>
              </div>


              <div>
                <span>
                  RISK
                </span>

                <strong>
                  {risk}
                </strong>
              </div>


              <div>
                <span>
                  PATHS FOUND
                </span>

                <strong>
                  {paths.length}
                </strong>
              </div>

            </div>

          </section>

        </section>


        {/* ATTACK PATH */}

        <section className="panel attack-panel">

          <div className="panel-header">

            <div>
              <span>
                TRACE
              </span>

              <h2>
                Potential Attack Paths
              </h2>
            </div>

            <div className="panel-count">
              {paths.length} result
              {paths.length === 1 ? "" : "s"}
            </div>

          </div>


          {paths.length === 0 ? (

            <div className="empty-result">

              <div className="empty-icon">
                —
              </div>

              <div>

                <strong>
                  No simulation result
                </strong>

                <p>
                  Select a source and target,
                  then run the analysis.
                </p>

              </div>

            </div>

          ) : (

            <div className="path-list">

              {paths.map((path, index) => (

                <div
                  className="path-row"
                  key={path.id}
                >

                  <div className="path-label">
                    PATH{" "}
                    {String(index + 1).padStart(
                      2,
                      "0"
                    )}
                  </div>


                  <div className="path-chain">

                    {path.nodes.map(
                      (nodeId, nodeIndex) => (

                        <div
                          className="path-step"
                          key={`${nodeId}-${nodeIndex}`}
                        >

                          <div className="path-node">

                            <strong>
                              {getNodeLabel(nodeId)}
                            </strong>

                            <small>
                              {getNodeType(nodeId)}
                            </small>

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

                </div>

              ))}

            </div>

          )}

        </section>


        {/* DEFENCE */}

        <section className="defence-grid">

          <div className="defence-card">

            <span>
              CURRENT STATE
            </span>

            <h3>
              {summary?.controls ?? 0}
              {" "}
              Controls
            </h3>

            <p>
              Defensive controls available
              in the digital twin.
            </p>

          </div>


          <div className="defence-card">

            <span>
              RISK ASSESSMENT
            </span>

            <h3>
              {risk}
            </h3>

            <p>
              Based on the simulated
              attack paths.
            </p>

          </div>


          <div className="defence-card">

            <span>
              NEXT ACTION
            </span>

            <h3>
              Review critical boundaries
            </h3>

            <p>
              Prioritise identity and
              high-value asset controls.
            </p>

          </div>

        </section>

      </main>


      <footer>
        SHADOWTWIN · Evidence-driven cyber risk analysis
      </footer>

    </div>
  );
}

export default App;