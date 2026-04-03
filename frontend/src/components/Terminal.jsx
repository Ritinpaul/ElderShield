import { useState, useRef, useCallback } from 'react'

export default function Terminal({ deepfakeLines, injectionLines }) {
  const [running, setRunning] = useState(false)
  const [btnText, setBtnText] = useState('▶ RUN DEEPFAKE')
  const bodyRef = useRef(null)
  const timeoutsRef = useRef([])

  const playTerminal = useCallback((lines) => {
    if (running) return
    setRunning(true)
    setBtnText('⏳ Running...')
    const body = bodyRef.current
    if (!body) return
    body.innerHTML = '<div class="tl"><span class="cmd">$ python demo/simulate_deepfake_call.py</span></div>'
    let delay = 500

    // Clear any previous timeouts
    timeoutsRef.current.forEach(t => clearTimeout(t))
    timeoutsRef.current = []

    lines.forEach(l => {
      delay += l.d
      const tid = setTimeout(() => {
        const div = document.createElement('div')
        div.className = 'tl'
        div.innerHTML = l.t || '&nbsp;'
        div.style.animation = 'fadeUp 0.3s ease'
        body.appendChild(div)
        body.scrollTop = body.scrollHeight
      }, delay)
      timeoutsRef.current.push(tid)
    })

    const finalTid = setTimeout(() => {
      setRunning(false)
      setBtnText('▶ RUN DEEPFAKE')
    }, delay + 500)
    timeoutsRef.current.push(finalTid)
  }, [running])

  const resetDemo = useCallback(() => {
    timeoutsRef.current.forEach(t => clearTimeout(t))
    timeoutsRef.current = []
    setRunning(false)
    setBtnText('▶ RUN DEEPFAKE')
    const body = bodyRef.current
    if (body) body.innerHTML = '<div class="tl"><span class="cmd">$ python demo/simulate_deepfake_call.py</span></div>'
  }, [])

  return (
    <>
      <div className="terminal" style={{marginBottom: '28px'}}>
        <div className="terminal-bar">
          <div className="dot dot-r"></div>
          <div className="dot dot-y"></div>
          <div className="dot dot-g"></div>
          <span className="terminal-label">ElderShield Terminal — CLI Execution</span>
        </div>
        <div className="terminal-body" id="terminalBody" ref={bodyRef}>
          <div className="tl"><span className="cmd">$ python demo/simulate_deepfake_call.py</span></div>
        </div>
      </div>

      <div style={{display: 'flex', gap: '12px'}}>
        <button
          className="btn btn-primary"
          id="runDemoBtn"
          onClick={() => playTerminal(deepfakeLines)}
          disabled={running}
          style={{background: '#ccff23', color: '#000'}}
        >
          {btnText}
        </button>
        <button
          className="btn btn-primary"
          onClick={() => playTerminal(injectionLines)}
          disabled={running}
          style={{background: '#9d50ff', color: '#fff'}}
        >
          🛡️ RUN INJECTION
        </button>
        <button className="btn btn-ghost" onClick={resetDemo}>🔄 RESET</button>
      </div>
    </>
  )
}
