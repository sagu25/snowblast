import { useState, useEffect } from 'react'
import TopBar from './components/TopBar.jsx'
import StatsRow from './components/StatsRow.jsx'
import LeftPane from './components/LeftPane.jsx'
import RadialView from './components/RadialView.jsx'
import CiGraphView from './components/CiGraphView.jsx'
import CiList from './components/CiList.jsx'
import AssessmentPanel from './components/AssessmentPanel.jsx'
import BottomBar from './components/BottomBar.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import { getAssessment, getCiGraph, getCiGraphById, postNote, ApiError } from './api.js'

export default function App() {
  const [theme, setTheme] = useState(
    () => (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'),
  )
  const [incidentNumber, setIncidentNumber] = useState(null)
  const [hours, setHours] = useState(6)
  const [assessment, setAssessment] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [posting, setPosting] = useState(false)
  const [postResult, setPostResult] = useState(null)

  const [tab, setTab] = useState('radius')
  const [ciGraph, setCiGraph] = useState(null)
  const [ciLoading, setCiLoading] = useState(false)
  const [ciError, setCiError] = useState(null)
  const [ciAttempted, setCiAttempted] = useState(false) // have we tried the incident's own CI yet?

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  function loadCiGraph(ciId) {
    setCiLoading(true)
    setCiError(null)
    const request = ciId ? getCiGraphById(ciId) : getCiGraph(incidentNumber)
    request
      .then((data) => setCiGraph(data))
      .catch((err) => setCiError(err instanceof ApiError ? err : new Error('Unexpected error')))
      .finally(() => setCiLoading(false))
  }

  useEffect(() => {
    if (tab !== 'ci' || !incidentNumber || ciAttempted || ciLoading) return
    setCiAttempted(true)
    loadCiGraph(null) // try the incident's own configuration item first, as a convenience default
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, incidentNumber])

  function handleSelectCi(ciId) {
    if (ciGraph && ciId === ciGraph.root) return
    loadCiGraph(ciId)
  }

  async function runLookup(number, hoursValue) {
    setIncidentNumber(number)
    setHours(hoursValue)
    setLoading(true)
    setError(null)
    setPostResult(null)
    setTab('radius')
    setCiGraph(null)
    setCiAttempted(false)
    setCiError(null)
    try {
      const data = await getAssessment(number, hoursValue)
      setAssessment(data)
    } catch (err) {
      setAssessment(null)
      setError(err instanceof ApiError ? err : new Error('Unexpected error'))
    } finally {
      setLoading(false)
    }
  }

  async function handleAccept() {
    if (!window.confirm(`Post this assessment to ${incidentNumber} as a ServiceNow work note?`)) return
    setPosting(true)
    setPostResult(null)
    try {
      await postNote(incidentNumber, true)
      setPostResult({ ok: true, message: `Posted to ${incidentNumber}.` })
    } catch (err) {
      setPostResult({ ok: false, message: err instanceof ApiError ? err.message : 'Failed to post.' })
    } finally {
      setPosting(false)
    }
  }

  function handleDeeper() {
    runLookup(incidentNumber, hours * 2)
  }

  function handleReject() {
    setPostResult({ ok: true, message: 'Assessment discarded. No ServiceNow write occurred.' })
  }

  return (
    <div className="shell">
      <TopBar onLookup={runLookup} loading={loading} theme={theme} onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))} />

      {assessment && <StatsRow assessment={assessment} />}

      <div className="main">
        <LeftPane assessment={assessment} />

        <div className="pane center">
          {loading && (
            <div className="center-loading">
              <div className="spinner" />
              <div className="small">Searching ServiceNow and scoring candidates…</div>
            </div>
          )}

          {!loading && error && (
            <div className="center-error">
              <div className="error-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="12" cy="12" r="10" /><path d="M12 8v5M12 16h.01" strokeLinecap="round" /></svg>
              </div>
              <div className="big">{error.code === 'servicenow_not_configured' ? 'ServiceNow not configured yet' : error.code === 'not_found' ? 'Incident not found' : 'Something went wrong'}</div>
              <div className="small">{error.message}</div>
            </div>
          )}

          {!loading && !error && !assessment && (
            <div className="center-empty">
              <div className="big">Look up an incident to begin</div>
              <div className="small">Type a ServiceNow incident number above (e.g. one printed by <code>python -m snow_agent.seed_incidents</code>) and click Analyze.</div>
            </div>
          )}

          {!loading && !error && assessment && (
            <>
              <div className="tabbar">
                <button className={'tab-btn' + (tab === 'radius' ? ' active' : '')} onClick={() => setTab('radius')}>Blast Radius Map</button>
                <button className={'tab-btn' + (tab === 'ci' ? ' active' : '')} onClick={() => setTab('ci')}>
                  CI Relationships<span className="tag">ServiceNow</span>
                </button>
              </div>

              {tab === 'radius' && (
                <>
                  <RadialView assessment={assessment} />
                  <BottomBar assessment={assessment} />
                </>
              )}

              {tab === 'ci' && (
                <div className="ci-tab-body">
                  <CiList selectedId={ciGraph?.root} onSelect={handleSelectCi} />

                  <div className="ci-graph-col">
                    {ciLoading && (
                      <div className="center-loading">
                        <div className="spinner" />
                        <div className="small">Fetching CI relationships from cmdb_rel_ci…</div>
                      </div>
                    )}
                    {!ciLoading && ciError && (
                      <div className="center-error">
                        <div className="big">{ciError.code === 'servicenow_not_configured' ? 'ServiceNow not configured yet' : 'Could not resolve this incident\'s configuration item'}</div>
                        <div className="small">{ciError.message}</div>
                        <div className="small">Pick a configuration item from the list to explore its relationships instead.</div>
                      </div>
                    )}
                    {!ciLoading && !ciError && ciGraph && (
                      <>
                        <CiGraphView graph={ciGraph} onSelect={handleSelectCi} />
                        <div className="bottom" style={{ gridTemplateColumns: '1fr' }}>
                          <div>
                            <div className="card-label">Source</div>
                            <div className="small" style={{ color: 'var(--text-2)', fontSize: 12 }}>
                              {ciGraph.nodes.length} configuration item(s) and {ciGraph.edges.length} relationship(s), fetched live from ServiceNow's <code>cmdb_ci</code> and <code>cmdb_rel_ci</code> tables for <strong>{ciGraph.root_label}</strong> — the same data behind ServiceNow's own CI relationship map.
                            </div>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {assessment ? (
          <AssessmentPanel
            assessment={assessment}
            onAccept={handleAccept}
            onDeeper={handleDeeper}
            onReject={handleReject}
            posting={posting}
            postResult={postResult}
          />
        ) : <div className="pane right" />}
      </div>

      {assessment && (
        <>
          <button className="chat-btn" onClick={() => setChatOpen((o) => !o)}>✦ Ask Blast Radius</button>
          {chatOpen && <ChatPanel incidentNumber={incidentNumber} onClose={() => setChatOpen(false)} />}
        </>
      )}
    </div>
  )
}
