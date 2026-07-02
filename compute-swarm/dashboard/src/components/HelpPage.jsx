import React from 'react'
import { HelpCircle, Briefcase, Cpu, CreditCard, BookOpen, Mail } from 'lucide-react'

const FAQS = [
  {
    q: 'What is ComputeSwarm?',
    a: 'ComputeSwarm is an open-source distributed computing platform. Researchers submit containerized scientific jobs (physics simulations, molecular docking, rendering), and volunteer workers run them on idle CPU/GPU hardware. The platform handles scheduling, validation, and credit-based rewards.',
  },
  {
    q: 'How do I submit a job?',
    a: 'Log in to the dashboard, click "New Job", choose a Docker image preset (or enter a custom one), set the number of work units and reward per unit, then upload your input files as a tar.gz archive. The orchestrator will split the job into work units and dispatch them to available workers.',
  },
  {
    q: 'How do I run a worker?',
    a: 'Install the worker client (Python 3.10+ required), run `python -m src.main --register` to create a worker identity, then start the daemon with `python -m src.main`. The worker will heartbeat with the orchestrator and automatically pull jobs.',
  },
  {
    q: 'How does pricing work?',
    a: 'Researchers purchase credits (1 credit ≈ $0.01 USD). Each job costs `work_unit_count × reward_per_unit` credits. Workers earn credits for each validated work unit they complete. Credits can be used for future jobs or withdrawn once Stripe Connect integration is live.',
  },
  {
    q: 'Is my data safe?',
    a: 'Yes. Input and output artifacts are stored in MinIO (S3-compatible) with presigned URLs that expire quickly. Worker containers run with network isolation and resource limits. The platform does not persist sensitive input data beyond the job lifecycle.',
  },
  {
    q: 'What job types are supported?',
    a: 'Any job that can run inside a Docker container. Built-in presets include Blender rendering, physics simulations, and molecular docking. You can also supply any public or private Docker image and a custom command.',
  },
  {
    q: 'How are results validated?',
    a: 'For MVP, completed work units are auto-validated if they have a checksum. In V2, the platform will dispatch validation replicas to multiple workers and compare SHA-256 checksums for redundant verification.',
  },
  {
    q: 'Can I cancel a job?',
    a: 'Yes. From the Jobs list or Job Detail page, click "Cancel Job". Pending and assigned work units will be marked as failed. Running units may complete if the worker is already executing them.',
  },
]

function Section({ icon: Icon, title, children }) {
  return (
    <div className="card">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-swarm-indigo-100">
          <Icon className="h-5 w-5 text-swarm-indigo-600" />
        </div>
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      </div>
      {children}
    </div>
  )
}

export default function HelpPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Help & FAQ</h1>
        <p className="text-sm text-slate-500">Common questions and getting-started guidance.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section icon={Briefcase} title="Submitting Jobs">
          <p className="text-sm text-slate-700">
            Go to <strong>New Job</strong> in the navigation bar. Pick a Docker image, set the number of work units (slices), and define a reward per unit. Upload your inputs as a tar.gz archive. The orchestrator handles the rest.
          </p>
        </Section>

        <Section icon={Cpu} title="Running a Worker">
          <p className="text-sm text-slate-700">
            Clone the worker code, install dependencies, and run <code className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono">python -m src.main --register</code>. The worker will auto-register and start claiming work units from the orchestrator.
          </p>
        </Section>

        <Section icon={CreditCard} title="Credits & Pricing">
          <p className="text-sm text-slate-700">
            Credits are the platform currency. You buy them (Stripe integration coming in V2) and spend them on jobs. Workers earn credits for validated work. 1 credit ≈ $0.01 USD.
          </p>
        </Section>

        <Section icon={BookOpen} title="Documentation">
          <p className="text-sm text-slate-700">
            For architecture details, API docs, and contributing guidelines, see the <code className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono">README.md</code>, <code className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono">ARCHITECTURE.md</code>, and <code className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono">CONTRIBUTING.md</code> in the repository.
          </p>
        </Section>
      </div>

      <div className="card">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-swarm-indigo-100">
            <HelpCircle className="h-5 w-5 text-swarm-indigo-600" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900">Frequently Asked Questions</h2>
        </div>
        <div className="space-y-4">
          {FAQS.map((faq, idx) => (
            <details key={idx} className="group rounded-lg border border-slate-200 p-4 open:bg-slate-50">
              <summary className="flex cursor-pointer list-none items-center justify-between font-medium text-slate-900">
                {faq.q}
                <span className="ml-2 transition group-open:rotate-180">▼</span>
              </summary>
              <p className="mt-2 text-sm leading-relaxed text-slate-700">{faq.a}</p>
            </details>
          ))}
        </div>
      </div>

      <div className="card flex items-center gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-swarm-indigo-100">
          <Mail className="h-5 w-5 text-swarm-indigo-600" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Still need help?</h2>
          <p className="text-sm text-slate-500">
            Open an issue on <a href="https://github.com/your-org/compute-swarm" className="text-swarm-indigo-600 hover:underline">GitHub</a> or contact the maintainers.
          </p>
        </div>
      </div>
    </div>
  )
}
