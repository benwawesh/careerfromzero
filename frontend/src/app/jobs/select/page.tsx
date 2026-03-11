'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { matchJobs, batchCustomize } from '@/lib/workflowApi';

interface MatchedJob {
  job_id: string;
  title: string;
  company: string;
  location: string;
  job_type: string;
  experience_level: string;
  salary_range: string;
  job_url: string;
  overall_match: number;
  skill_match: number;
  experience_match: number;
  matched_skills: string[];
  missing_skills: string[];
  suggestions: string[];
}

function JobSelectionContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const cvId = searchParams.get('cv_id');

  const [jobs, setJobs] = useState<MatchedJob[]>([]);
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [customizing, setCustomizing] = useState(false);
  const [error, setError] = useState('');
  const [generateCoverLetter, setGenerateCoverLetter] = useState(false);
  const [progress, setProgress] = useState<{ current: number; total: number; percentage: number } | null>(null);

  useEffect(() => {
    if (cvId) {
      loadJobs();
    } else {
      setError('No CV ID provided');
      setLoading(false);
    }
  }, [cvId]);

  const loadJobs = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await matchJobs({
        cv_id: cvId!,
        min_score: 60,
        limit: 100,
      });

      if (response.status === 'success') {
        setJobs(response.jobs);
      } else {
        setError(response.error || 'Failed to load jobs');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  };

  const handleJobToggle = (jobId: string) => {
    const newSelected = new Set(selectedJobs);
    if (newSelected.has(jobId)) {
      newSelected.delete(jobId);
    } else {
      newSelected.add(jobId);
    }
    setSelectedJobs(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedJobs.size === jobs.length) {
      setSelectedJobs(new Set());
    } else {
      setSelectedJobs(new Set(jobs.map(job => job.job_id)));
    }
  };

  const handleGenerate = async () => {
    if (selectedJobs.size === 0) {
      setError('Please select at least one job');
      return;
    }

    try {
      setCustomizing(true);
      setError('');
      setProgress({ current: 0, total: selectedJobs.size, percentage: 0 });

      const response = await batchCustomize({
        cv_id: cvId!,
        job_ids: Array.from(selectedJobs),
        options: {
          generate_cv: true,
          generate_cover_letter: generateCoverLetter,
          save_as_drafts: true,
        },
      });

      if (response.status === 'success' || response.status === 'partial') {
        // Navigate to preview page
        router.push(`/jobs/preview?cv_id=${cvId}&count=${response.completed}`);
      } else {
        setError(response.error || 'Failed to generate customizations');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate customizations');
    } finally {
      setCustomizing(false);
      setProgress(null);
    }
  };

  const getMatchColor = (score: number) => {
    if (score >= 85) return 'bg-green-100 text-green-800 border-green-300';
    if (score >= 70) return 'bg-blue-100 text-blue-800 border-blue-300';
    return 'bg-yellow-100 text-yellow-800 border-yellow-300';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading matched jobs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Select Jobs to Apply To</h1>
          <p className="mt-2 text-gray-600">
            Found {jobs.length} matching jobs. Select the ones you want to generate custom CVs for.
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Filters and Actions */}
        <div className="mb-6 bg-white rounded-lg shadow p-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={selectedJobs.size === jobs.length && jobs.length > 0}
                  onChange={handleSelectAll}
                  className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                />
                <span className="ml-2 text-gray-700">
                  {selectedJobs.size === jobs.length ? 'Deselect All' : 'Select All'}
                </span>
              </label>
              
              <span className="text-gray-600">
                {selectedJobs.size} of {jobs.length} selected
              </span>
            </div>

            <div className="flex items-center gap-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={generateCoverLetter}
                  onChange={(e) => setGenerateCoverLetter(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                />
                <span className="ml-2 text-gray-700">Generate Cover Letters</span>
              </label>

              <button
                onClick={handleGenerate}
                disabled={customizing || selectedJobs.size === 0}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {customizing ? 'Generating...' : `Generate CVs for ${selectedJobs.size} jobs`}
              </button>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        {progress && (
          <div className="mb-6 bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">
                Generating customizations...
              </span>
              <span className="text-sm text-gray-600">
                {progress.current} / {progress.total}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${progress.percentage}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Jobs List */}
        <div className="space-y-4">
          {jobs.map((job) => (
            <div
              key={job.job_id}
              className={`bg-white rounded-lg shadow p-6 border-2 transition-all ${
                selectedJobs.has(job.job_id)
                  ? 'border-blue-500 ring-2 ring-blue-200'
                  : 'border-transparent hover:border-gray-300'
              }`}
            >
              <div className="flex items-start gap-4">
                {/* Checkbox */}
                <input
                  type="checkbox"
                  checked={selectedJobs.has(job.job_id)}
                  onChange={() => handleJobToggle(job.job_id)}
                  className="mt-1 w-5 h-5 text-blue-600 rounded border-gray-300 focus:ring-blue-500 cursor-pointer"
                />

                {/* Job Details */}
                <div className="flex-1">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900 mb-1">
                        {job.title}
                      </h2>
                      <p className="text-gray-600">{job.company}</p>
                    </div>
                    <div className={`px-3 py-1 rounded-full text-sm font-medium border ${getMatchColor(job.overall_match)}`}>
                      {job.overall_match}% Match
                    </div>
                  </div>

                  {/* Job Meta */}
                  <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-4">
                    {job.location && (
                      <span className="flex items-center">
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        {job.location}
                      </span>
                    )}
                    {job.job_type && (
                      <span className="flex items-center">
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                        {job.job_type}
                      </span>
                    )}
                    {job.salary_range && (
                      <span className="flex items-center">
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {job.salary_range}
                      </span>
                    )}
                  </div>

                  {/* Match Details */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Skill Match</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-green-600 h-2 rounded-full"
                            style={{ width: `${job.skill_match}%` }}
                          ></div>
                        </div>
                        <span className="text-sm font-medium text-gray-700">{job.skill_match}%</span>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Experience Match</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${job.experience_match}%` }}
                          ></div>
                        </div>
                        <span className="text-sm font-medium text-gray-700">{job.experience_match}%</span>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Overall Match</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-purple-600 h-2 rounded-full"
                            style={{ width: `${job.overall_match}%` }}
                          ></div>
                        </div>
                        <span className="text-sm font-medium text-gray-700">{job.overall_match}%</span>
                      </div>
                    </div>
                  </div>

                  {/* Matched Skills */}
                  <div className="mb-4">
                    <p className="text-xs font-medium text-gray-500 mb-2">Matched Skills</p>
                    <div className="flex flex-wrap gap-2">
                      {job.matched_skills.slice(0, 8).map((skill, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full"
                        >
                          {skill}
                        </span>
                      ))}
                      {job.matched_skills.length > 8 && (
                        <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
                          +{job.matched_skills.length - 8} more
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Missing Skills */}
                  {job.missing_skills.length > 0 && (
                    <div className="mb-4">
                      <p className="text-xs font-medium text-gray-500 mb-2">Missing Skills</p>
                      <div className="flex flex-wrap gap-2">
                        {job.missing_skills.slice(0, 5).map((skill, index) => (
                          <span
                            key={index}
                            className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full"
                          >
                            {skill}
                          </span>
                        ))}
                        {job.missing_skills.length > 5 && (
                          <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
                            +{job.missing_skills.length - 5} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Suggestions */}
                  {job.suggestions.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-2">Suggestions</p>
                      <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                        {job.suggestions.slice(0, 3).map((suggestion, index) => (
                          <li key={index}>{suggestion}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* View Job Button */}
                  {job.job_url && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <a
                        href={job.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                      >
                        View Full Job Posting →
                      </a>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* No Jobs Found */}
        {jobs.length === 0 && !loading && (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No jobs found</h3>
            <p className="mt-1 text-sm text-gray-500">
              Try adjusting your filters or upload a different CV
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function JobSelectionPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    }>
      <JobSelectionContent />
    </Suspense>
  );
}