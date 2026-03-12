'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import ProtectedRoute from '@/components/ProtectedRoute'
import { apiFetch } from '@/lib/apiFetch'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ExperienceEntry {
  company: string
  role: string
  start_date: string
  end_date: string
  description: string
  enhance: boolean   // "make this stronger"
  create: boolean    // "I have nothing — Claude creates this"
}

interface ProjectEntry {
  name: string
  description: string
  technologies: string
  link: string
  enhance: boolean
}

interface EducationEntry {
  degree: string
  institution: string
  year: string
  grade: string
}

interface FormData {
  // Personal
  name: string
  phone: string
  email: string
  location: string
  linkedin: string
  github: string
  portfolio: string
  // Summary
  summary: string
  claude_write_summary: boolean
  // Experience
  experience: ExperienceEntry[]
  // Projects
  projects: ProjectEntry[]
  claude_create_projects: boolean
  // Skills
  skills: string
  claude_add_skills: boolean
  // Education
  education: EducationEntry[]
  // Certifications
  certifications: string
  claude_suggest_certifications: boolean
  // Job target
  job_title: string
  job_company: string
  job_description: string
}

interface ReviewSection {
  section: string
  label: string
  original: string
  enhanced: string
  approved: string  // what the user edits/approves
  was_invented: boolean
}

const STEPS = [
  { id: 'personal',       label: 'Personal Info' },
  { id: 'summary',        label: 'Summary' },
  { id: 'experience',     label: 'Experience' },
  { id: 'projects',       label: 'Projects' },
  { id: 'skills',         label: 'Skills' },
  { id: 'education',      label: 'Education' },
  { id: 'certifications', label: 'Certifications' },
  { id: 'job',            label: 'Target Job' },
  { id: 'review',         label: 'Review & Approve' },
]

const emptyExp = (): ExperienceEntry => ({
  company: '', role: '', start_date: '', end_date: '',
  description: '', enhance: false, create: false,
})

const emptyProject = (): ProjectEntry => ({
  name: '', description: '', technologies: '', link: '', enhance: false,
})

const emptyEdu = (): EducationEntry => ({
  degree: '', institution: '', year: '', grade: '',
})

const initialForm: FormData = {
  name: '', phone: '', email: '', location: '',
  linkedin: '', github: '', portfolio: '',
  summary: '', claude_write_summary: false,
  experience: [emptyExp()],
  projects: [emptyProject()],
  claude_create_projects: false,
  skills: '', claude_add_skills: true,
  education: [emptyEdu()],
  certifications: '', claude_suggest_certifications: false,
  job_title: '', job_company: '', job_description: '',
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function CVBuilderPage() {
  return (
    <ProtectedRoute>
      <CVBuilder />
    </ProtectedRoute>
  )
}

function CVBuilder() {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [form, setForm] = useState<FormData>(initialForm)
  const [generating, setGenerating] = useState(false)
  const [reviews, setReviews] = useState<ReviewSection[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // ── Helpers ────────────────────────────────────────────────────────────────

  const set = (field: keyof FormData, value: unknown) =>
    setForm(f => ({ ...f, [field]: value }))

  const setExp = (i: number, field: keyof ExperienceEntry, value: unknown) =>
    setForm(f => {
      const exp = [...f.experience]
      exp[i] = { ...exp[i], [field]: value }
      return { ...f, experience: exp }
    })

  const setProj = (i: number, field: keyof ProjectEntry, value: unknown) =>
    setForm(f => {
      const projs = [...f.projects]
      projs[i] = { ...projs[i], [field]: value }
      return { ...f, projects: projs }
    })

  const setEdu = (i: number, field: keyof EducationEntry, value: unknown) =>
    setForm(f => {
      const edu = [...f.education]
      edu[i] = { ...edu[i], [field]: value }
      return { ...f, education: edu }
    })

  const next = () => setStep(s => Math.min(s + 1, STEPS.length - 1))
  const back = () => setStep(s => Math.max(s - 1, 0))

  // ── Generate — calls Claude to enhance/invent ──────────────────────────────

  const generate = async () => {
    if (!form.job_description.trim()) {
      setError('Please paste the job description before generating.')
      return
    }
    setError('')
    setGenerating(true)
    try {
      const res = await apiFetch('/api/cv/builder/enhance/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.error || 'Enhancement failed'); return }
      setReviews(data.sections.map((s: ReviewSection) => ({ ...s, approved: s.enhanced })))
      next()
    } catch {
      setError('Network error. Is the backend running?')
    } finally {
      setGenerating(false)
    }
  }

  // ── Save — saves approved data as a real CV ────────────────────────────────

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      const approved: Record<string, string> = {}
      reviews.forEach(r => { approved[r.section] = r.approved })
      const res = await apiFetch('/api/cv/create-manual/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ form, approved }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.error || 'Save failed'); return }
      router.push(`/cv/${data.id}`)
    } catch {
      setError('Network error. Is the backend running?')
    } finally {
      setSaving(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  const currentStep = STEPS[step]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">CV Builder</h1>
            <p className="text-sm text-gray-500">Step {step + 1} of {STEPS.length} — {currentStep.label}</p>
          </div>
          <button onClick={() => router.push('/cv')} className="text-sm text-gray-500 hover:text-gray-700">
            ← Back to CVs
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-gray-200">
        <div
          className="h-1 bg-blue-600 transition-all duration-300"
          style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
        />
      </div>

      <div className="max-w-3xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* ── STEP: Personal Info ── */}
        {currentStep.id === 'personal' && (
          <StepCard title="Personal Information" subtitle="Your contact details — these will not be invented by Claude">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Full Name *" value={form.name} onChange={v => set('name', v)} placeholder="Benson Waweru" />
              <Field label="Phone *" value={form.phone} onChange={v => set('phone', v)} placeholder="+254 700 000 000" />
              <Field label="Email *" value={form.email} onChange={v => set('email', v)} placeholder="you@email.com" type="email" />
              <Field label="Location" value={form.location} onChange={v => set('location', v)} placeholder="Nairobi, Kenya" />
              <Field label="LinkedIn URL" value={form.linkedin} onChange={v => set('linkedin', v)} placeholder="linkedin.com/in/yourname" />
              <Field label="GitHub URL" value={form.github} onChange={v => set('github', v)} placeholder="github.com/yourname" />
              <Field label="Portfolio URL" value={form.portfolio} onChange={v => set('portfolio', v)} placeholder="yourportfolio.com" className="col-span-2" />
            </div>
          </StepCard>
        )}

        {/* ── STEP: Summary ── */}
        {currentStep.id === 'summary' && (
          <StepCard title="Professional Summary" subtitle="A 3-4 sentence overview of who you are professionally">
            <Checkbox
              checked={form.claude_write_summary}
              onChange={v => set('claude_write_summary', v)}
              label="Let Claude write my professional summary based on the job I'm applying for"
              highlight
            />
            {!form.claude_write_summary && (
              <TextArea
                label="Your Summary (optional)"
                value={form.summary}
                onChange={v => set('summary', v)}
                placeholder="Write a brief professional summary, or tick the box above to let Claude write one tailored to your target job."
                rows={5}
              />
            )}
            {form.claude_write_summary && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-700">
                Claude will write a powerful, targeted professional summary after you provide the job description in the final step.
              </div>
            )}
          </StepCard>
        )}

        {/* ── STEP: Experience ── */}
        {currentStep.id === 'experience' && (
          <StepCard title="Work Experience" subtitle="Add your work history. Claude can enhance weak entries or create entries if you have none.">
            {form.experience.map((exp, i) => (
              <div key={i} className="border border-gray-200 rounded-xl p-5 mb-4 space-y-3 bg-white">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-900">Experience {i + 1}</h3>
                  {form.experience.length > 1 && (
                    <button
                      onClick={() => setForm(f => ({ ...f, experience: f.experience.filter((_, j) => j !== i) }))}
                      className="text-red-400 hover:text-red-600 text-sm"
                    >
                      Remove
                    </button>
                  )}
                </div>

                <Checkbox
                  checked={exp.create}
                  onChange={v => setExp(i, 'create', v)}
                  label="I don't have relevant experience for this role — Claude can create a believable entry"
                  highlight
                />

                {!exp.create && (
                  <>
                    <div className="grid grid-cols-2 gap-3">
                      <Field label="Company" value={exp.company} onChange={v => setExp(i, 'company', v)} placeholder="Company Name" />
                      <Field label="Role / Job Title" value={exp.role} onChange={v => setExp(i, 'role', v)} placeholder="Software Developer" />
                      <Field label="Start Date" value={exp.start_date} onChange={v => setExp(i, 'start_date', v)} placeholder="Jan 2022" />
                      <Field label="End Date" value={exp.end_date} onChange={v => setExp(i, 'end_date', v)} placeholder="Present" />
                    </div>
                    <TextArea
                      label="What did you do? (brief notes are fine)"
                      value={exp.description}
                      onChange={v => setExp(i, 'description', v)}
                      placeholder="e.g. Built websites, managed servers, worked with clients..."
                      rows={3}
                    />
                    <Checkbox
                      checked={exp.enhance}
                      onChange={v => setExp(i, 'enhance', v)}
                      label="My description above is weak or incomplete — Claude should enhance and expand it"
                    />
                  </>
                )}
              </div>
            ))}

            <button
              onClick={() => setForm(f => ({ ...f, experience: [...f.experience, emptyExp()] }))}
              className="w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-blue-400 hover:text-blue-600 text-sm font-medium transition-colors"
            >
              + Add Another Experience
            </button>
          </StepCard>
        )}

        {/* ── STEP: Projects ── */}
        {currentStep.id === 'projects' && (
          <StepCard title="Projects" subtitle="Real projects you have built. Claude can create realistic projects if you don't have enough.">
            <Checkbox
              checked={form.claude_create_projects}
              onChange={v => set('claude_create_projects', v)}
              label="I don't have enough projects — Claude can create 2-3 relevant projects tailored to the target job"
              highlight
            />

            <div className="mt-4 space-y-4">
              {form.projects.map((proj, i) => (
                <div key={i} className="border border-gray-200 rounded-xl p-5 space-y-3 bg-white">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium text-gray-900">Project {i + 1}</h3>
                    {form.projects.length > 1 && (
                      <button
                        onClick={() => setForm(f => ({ ...f, projects: f.projects.filter((_, j) => j !== i) }))}
                        className="text-red-400 hover:text-red-600 text-sm"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Project Name" value={proj.name} onChange={v => setProj(i, 'name', v)} placeholder="Job Matching Platform" />
                    <Field label="Link (if any)" value={proj.link} onChange={v => setProj(i, 'link', v)} placeholder="github.com/you/project" />
                  </div>
                  <Field label="Technologies Used" value={proj.technologies} onChange={v => setProj(i, 'technologies', v)} placeholder="React, Node.js, PostgreSQL" />
                  <TextArea
                    label="Description"
                    value={proj.description}
                    onChange={v => setProj(i, 'description', v)}
                    placeholder="What does it do? What problem does it solve?"
                    rows={2}
                  />
                  <Checkbox
                    checked={proj.enhance}
                    onChange={v => setProj(i, 'enhance', v)}
                    label="Claude should enhance and expand this project description"
                  />
                </div>
              ))}
            </div>

            <button
              onClick={() => setForm(f => ({ ...f, projects: [...f.projects, emptyProject()] }))}
              className="w-full mt-2 py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-blue-400 hover:text-blue-600 text-sm font-medium transition-colors"
            >
              + Add Another Project
            </button>
          </StepCard>
        )}

        {/* ── STEP: Skills ── */}
        {currentStep.id === 'skills' && (
          <StepCard title="Skills" subtitle="List the skills you actually have. Claude can add the skills the job requires that you're missing.">
            <TextArea
              label="Your Skills (comma separated or one per line)"
              value={form.skills}
              onChange={v => set('skills', v)}
              placeholder="PHP, JavaScript, Node.js, MySQL, React, Flutter, Docker..."
              rows={4}
            />
            <Checkbox
              checked={form.claude_add_skills}
              onChange={v => set('claude_add_skills', v)}
              label="Claude should add relevant skills from the job description that I haven't listed (presented naturally)"
              highlight
            />
          </StepCard>
        )}

        {/* ── STEP: Education ── */}
        {currentStep.id === 'education' && (
          <StepCard title="Education" subtitle="Your academic qualifications — these will not be invented by Claude">
            {form.education.map((edu, i) => (
              <div key={i} className="border border-gray-200 rounded-xl p-5 mb-4 space-y-3 bg-white">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-900">Education {i + 1}</h3>
                  {form.education.length > 1 && (
                    <button
                      onClick={() => setForm(f => ({ ...f, education: f.education.filter((_, j) => j !== i) }))}
                      className="text-red-400 hover:text-red-600 text-sm"
                    >
                      Remove
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Degree / Qualification" value={edu.degree} onChange={v => setEdu(i, 'degree', v)} placeholder="BSc Information Technology" />
                  <Field label="Institution" value={edu.institution} onChange={v => setEdu(i, 'institution', v)} placeholder="University of Nairobi" />
                  <Field label="Year Completed" value={edu.year} onChange={v => setEdu(i, 'year', v)} placeholder="2022" />
                  <Field label="Grade / Division" value={edu.grade} onChange={v => setEdu(i, 'grade', v)} placeholder="Second Class Upper" />
                </div>
              </div>
            ))}
            <button
              onClick={() => setForm(f => ({ ...f, education: [...f.education, emptyEdu()] }))}
              className="w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-blue-400 hover:text-blue-600 text-sm font-medium transition-colors"
            >
              + Add Another Qualification
            </button>
          </StepCard>
        )}

        {/* ── STEP: Certifications ── */}
        {currentStep.id === 'certifications' && (
          <StepCard
            title="Certifications"
            subtitle='Certifications are official credentials that boost your ATS score — e.g. "AWS Certified Developer", "Google Cloud Professional". You earn these by completing short courses on platforms like Coursera, Udemy, or directly from AWS/Google.'
          >
            <TextArea
              label="Certifications you already have (one per line)"
              value={form.certifications}
              onChange={v => set('certifications', v)}
              placeholder="e.g. Meta React Developer Certificate&#10;Google IT Support Certificate"
              rows={4}
            />
            <Checkbox
              checked={form.claude_suggest_certifications}
              onChange={v => set('claude_suggest_certifications', v)}
              label='Claude can add "Currently pursuing: [relevant cert]" — honest, shows initiative, boosts ATS score'
              highlight
            />
            <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
              <strong>Why this matters for Davis & Shirtliff:</strong> Adding "Currently pursuing AWS Certified Developer" or "Kubernetes Administrator (CKA)" signals you are investing in exactly the skills they need. Recruiters see this positively.
            </div>
          </StepCard>
        )}

        {/* ── STEP: Target Job ── */}
        {currentStep.id === 'job' && (
          <StepCard title="Target Job" subtitle="Tell Claude exactly which job you are applying for. This is what everything gets tailored to.">
            <div className="grid grid-cols-2 gap-4 mb-4">
              <Field label="Job Title" value={form.job_title} onChange={v => set('job_title', v)} placeholder="Software Developer" />
              <Field label="Company Name" value={form.job_company} onChange={v => set('job_company', v)} placeholder="Davis & Shirtliff" />
            </div>
            <TextArea
              label="Paste the full job description here *"
              value={form.job_description}
              onChange={v => set('job_description', v)}
              placeholder="Paste the complete job description including requirements, responsibilities, qualifications..."
              rows={12}
            />
          </StepCard>
        )}

        {/* ── STEP: Review & Approve ── */}
        {currentStep.id === 'review' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-md p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-1">Review Claude's Work</h2>
              <p className="text-sm text-gray-500">
                Read each section below. Edit anything you want to change. When you're happy, click <strong>Save & Create CV</strong>.
              </p>
            </div>

            {reviews.map((r, i) => (
              <div key={i} className="bg-white rounded-xl shadow-md p-6 space-y-3">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-gray-900">{r.label}</h3>
                  {r.was_invented && (
                    <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">
                      Created by Claude
                    </span>
                  )}
                  {!r.was_invented && r.original !== r.enhanced && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                      Enhanced by Claude
                    </span>
                  )}
                </div>

                {r.original && r.original !== r.enhanced && (
                  <div className="text-xs text-gray-400 bg-gray-50 rounded p-3 line-through">
                    Original: {r.original}
                  </div>
                )}

                <TextArea
                  label="Approved version (edit as needed)"
                  value={r.approved}
                  onChange={v => setReviews(prev => prev.map((rev, j) => j === i ? { ...rev, approved: v } : rev))}
                  rows={r.approved.split('\n').length + 2}
                />
              </div>
            ))}

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
            )}

            <button
              onClick={save}
              disabled={saving}
              className="w-full bg-green-600 text-white py-4 rounded-xl font-semibold text-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {saving ? (
                <><span className="animate-spin">⏳</span> Saving CV...</>
              ) : (
                '✓ Save & Create CV'
              )}
            </button>
          </div>
        )}

        {/* ── Navigation ── */}
        {currentStep.id !== 'review' && (
          <div className="mt-6 flex justify-between">
            <button
              onClick={back}
              disabled={step === 0}
              className="px-6 py-3 border border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50 disabled:opacity-40 font-medium"
            >
              ← Back
            </button>

            {currentStep.id === 'job' ? (
              <button
                onClick={generate}
                disabled={generating || !form.job_description.trim()}
                className="px-8 py-3 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
              >
                {generating ? (
                  <><span className="animate-spin inline-block">⏳</span> Claude is working...</>
                ) : (
                  '✨ Generate & Review'
                )}
              </button>
            ) : (
              <button
                onClick={next}
                className="px-8 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700"
              >
                Next →
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Small reusable components ──────────────────────────────────────────────────

function StepCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl shadow-md p-6 space-y-4">
      <div>
        <h2 className="text-lg font-bold text-gray-900">{title}</h2>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

function Field({
  label, value, onChange, placeholder, type = 'text', className = '',
}: {
  label: string; value: string; onChange: (v: string) => void
  placeholder?: string; type?: string; className?: string
}) {
  return (
    <div className={className}>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  )
}

function TextArea({
  label, value, onChange, placeholder, rows = 3,
}: {
  label: string; value: string; onChange: (v: string) => void
  placeholder?: string; rows?: number
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      <textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
      />
    </div>
  )
}

function Checkbox({
  checked, onChange, label, highlight = false,
}: {
  checked: boolean; onChange: (v: boolean) => void; label: string; highlight?: boolean
}) {
  return (
    <label className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
      highlight
        ? checked ? 'bg-purple-50 border border-purple-200' : 'bg-gray-50 border border-gray-200 hover:bg-purple-50'
        : checked ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50 border border-gray-200 hover:bg-blue-50'
    }`}>
      <input
        type="checkbox"
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 rounded border-gray-300 accent-purple-600"
      />
      <span className={`text-sm ${highlight ? 'text-purple-800 font-medium' : 'text-gray-700'}`}>{label}</span>
    </label>
  )
}
