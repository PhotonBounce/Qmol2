import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { useToast } from '../components/Toast'
import { AlertCircle, Upload, Plus, X, Loader2, CheckCircle } from 'lucide-react'

const DOCKER_PRESETS = [
  { value: 'computeswarm/blender-render:latest', label: 'Blender Render' },
  { value: 'computeswarm/physics-sim:latest', label: 'Physics Simulation' },
  { value: 'computeswarm/molecular-dock:latest', label: 'Molecular Docking' },
]

export default function JobSubmit() {
  const navigate = useNavigate()
  const { addToast } = useToast()
  const fileInputRef = useRef(null)
  const [name, setName] = useState('')
  const [dockerImage, setDockerImage] = useState(DOCKER_PRESETS[0].value)
  const [customCommand, setCustomCommand] = useState('')
  const [envVars, setEnvVars] = useState([{ key: '', value: '' }])
  const [inputFile, setInputFile] = useState(null)
  const [workUnitCount, setWorkUnitCount] = useState(1)
  const [rewardPerUnit, setRewardPerUnit] = useState(1.0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const addEnvVar = () => setEnvVars([...envVars, { key: '', value: '' }])
  const removeEnvVar = (idx) => setEnvVars(envVars.filter((_, i) => i !== idx))
  const updateEnvVar = (idx, field, value) => {
    const next = [...envVars]
    next[idx][field] = value
    setEnvVars(next)
  }

  const resetForm = () => {
    setName('')
    setDockerImage(DOCKER_PRESETS[0].value)
    setCustomCommand('')
    setEnvVars([{ key: '', value: '' }])
    setInputFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    setWorkUnitCount(1)
    setRewardPerUnit(1.0)
    setError('')
    setSuccess('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    const envVarsObj = {}
    envVars.forEach(({ key, value }) => {
      if (key.trim()) envVarsObj[key.trim()] = value
    })

    const payload = {
      name,
      docker_image: dockerImage,
      command: customCommand,
      env_vars: envVarsObj,
      work_unit_count: Number(workUnitCount),
      reward_per_unit: Number(rewardPerUnit),
    }

    try {
      const res = await api.post('/jobs', payload)
      const jobId = res.data.job_id
      const uploadUrls = res.data.input_upload_urls || []

      if (inputFile && uploadUrls.length > 0) {
        try {
          await Promise.all(
            uploadUrls.map((url) =>
              fetch(url, {
                method: 'PUT',
                body: inputFile,
                headers: {
                  'Content-Type': inputFile.type || 'application/octet-stream',
                },
              }).then((r) => {
                if (!r.ok) throw new Error(`Upload failed: ${r.status} ${r.statusText}`)
              })
            )
          )
        } catch (uploadErr) {
          setError(`Job created but input file upload failed: ${uploadErr.message}. You may need to resubmit.`)
          addToast(`Upload failed: ${uploadErr.message}`, 'error')
          setLoading(false)
          return
        }
      }

      setSuccess('Job submitted successfully!')
      addToast('Job submitted successfully', 'success')
      resetForm()
      navigate(`/jobs/${jobId}`)
    } catch (err) {
      setError(err.message || 'Failed to submit job')
      addToast(err.message || 'Failed to submit job', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Submit New Job</h1>
        <p className="text-sm text-slate-500">Configure your containerized compute job and set worker rewards.</p>
      </div>

      <div className="card">
        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-green-50 p-3 text-sm text-green-700">
            <CheckCircle className="h-4 w-4 shrink-0" />
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className="mb-1 block text-sm font-medium text-slate-700">Job Name</label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input-field"
                placeholder="e.g., Blender Frame Render Batch 1"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Docker Image</label>
              <select
                value={dockerImage}
                onChange={(e) => setDockerImage(e.target.value)}
                className="input-field"
              >
                {DOCKER_PRESETS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Custom Command</label>
              <input
                value={customCommand}
                onChange={(e) => setCustomCommand(e.target.value)}
                className="input-field"
                placeholder="Override container CMD"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Number of Work Units</label>
              <input
                type="number"
                min={1}
                required
                value={workUnitCount}
                onChange={(e) => setWorkUnitCount(e.target.value)}
                className="input-field"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Reward per Unit (credits)</label>
              <input
                type="number"
                step="0.1"
                min={0.1}
                required
                value={rewardPerUnit}
                onChange={(e) => setRewardPerUnit(e.target.value)}
                className="input-field"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Environment Variables</label>
            <div className="space-y-2">
              {envVars.map((ev, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <input
                    value={ev.key}
                    onChange={(e) => updateEnvVar(idx, 'key', e.target.value)}
                    placeholder="KEY"
                    className="input-field flex-1"
                  />
                  <span className="text-slate-400">=</span>
                  <input
                    value={ev.value}
                    onChange={(e) => updateEnvVar(idx, 'value', e.target.value)}
                    placeholder="value"
                    className="input-field flex-1"
                  />
                  {envVars.length > 1 && (
                    <button type="button" onClick={() => removeEnvVar(idx)} className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600">
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
              <button type="button" onClick={addEnvVar} className="btn-secondary mt-2">
                <Plus className="mr-1 h-4 w-4" /> Add Variable
              </button>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Input Files</label>
            <div className="rounded-lg border-2 border-dashed border-slate-300 p-6 text-center hover:border-swarm-indigo-400 transition-colors relative">
              <Upload className="mx-auto h-8 w-8 text-slate-400" />
              <p className="mt-2 text-sm text-slate-600">
                {inputFile ? inputFile.name : 'Drag and drop a tar.gz archive, or click to browse'}
              </p>
              <input
                type="file"
                accept=".tar.gz,.tgz,.zip"
                ref={fileInputRef}
                onChange={(e) => setInputFile(e.target.files[0])}
                className="absolute inset-0 cursor-pointer opacity-0 w-full h-full"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button type="button" onClick={() => navigate('/jobs')} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Submitting…
                </>
              ) : (
                'Submit Job'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
