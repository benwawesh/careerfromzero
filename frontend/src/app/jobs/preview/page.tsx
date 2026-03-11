'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { listApplications } from '@/lib/workflowApi';

interface Application {
  id: string;
  job_title: string;
  company: string;
  location: string;
  status: string;
  mode: string;
  application_date: string;
  match_score: number;
  job_url: string;
}

export default function PreviewPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const cvId = searchParams.get('cv_id');
  const count = parseInt(searchParams.get('count') || '0');

  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    loadApplications();
  }, []);

  const loadApplications = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await listApplications({ status: 'draft' });

      if (response.applications) {
        setApplications(response.applications);
        if (response.applications.length > 0) {
          setSelectedApp(response.applications[0]);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load applications');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadCV = (applicationId: string) => {
    // Navigate to CV download page
    router.push(`/cv/${applicationId}/download`);
  };

  const handleDownloadCoverLetter = (applicationId: string) => {
    // For now, just alert - implement actual download
    alert('Cover letter download feature coming soon!');
  };

  const handleApplyNow = (jobUrl: string, applicationId: string) => {
    // Open job application URL in new tab
    if (jobUrl) {
      window.open(jobUrl, '_blank');
    } else {
      alert('No job application URL available');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading customizations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Preview & Download Customized CVs
          </h1>
          <p className="mt-2 text-gray-600">
            Review your customized CVs and cover letters before applying
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Success Message */}
        {!error && applications.length > 0 && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-green-800">
              ✅ Successfully generated customizations for {count || applications.length} jobs!
            </p>
          </div>
        )}

        {applications.length === 0 ? (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No customizations found</h3>
            <p className="mt-1 text-sm text-gray-500">
              Go back and select jobs to generate customizations
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column - Applications List */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-lg shadow">
                <div className="p-4 border-b border-gray-200">
                  <h2 className="font-semibold text-gray-900">
                    {applications.length} Customizations
                  </h2>
                </div>
                <div className="divide-y divide-gray-200">
                  {applications.map((app) => (
                    <button
                      key={app.id}
                      onClick={() => setSelectedApp(app)}
                      className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
                        selectedApp?.id === app.id
                          ? 'bg-blue-50 border-l-4 border-blue-600'
                          : ''
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-medium text-gray-900 text-sm">
                            {app.job_title}
                          </h3>
                          <p className="text-sm text-gray-600 mt-1">
                            {app.company}
                          </p>
                          {app.location && (
                            <p className="text-xs text-gray-500 mt-1">
                              {app.location}
                            </p>
                          )}
                        </div>
                        <div className="ml-4">
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            {app.match_score}%
                          </span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Column - Preview */}
            <div className="lg:col-span-2">
              {selectedApp && (
                <div className="space-y-6">
                  {/* Job Info Card */}
                  <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h2 className="text-2xl font-bold text-gray-900">
                          {selectedApp.job_title}
                        </h2>
                        <p className="text-lg text-gray-600 mt-1">
                          {selectedApp.company}
                        </p>
                      </div>
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                        {selectedApp.match_score}% Match
                      </span>
                    </div>

                    {selectedApp.location && (
                      <div className="flex items-center text-gray-600 mb-2">
                        <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        {selectedApp.location}
                      </div>
                    )}

                    {selectedApp.job_url && (
                      <a
                        href={selectedApp.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center text-blue-600 hover:text-blue-800 text-sm font-medium"
                      >
                        View Full Job Posting
                        <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </a>
                    )}
                  </div>

                  {/* Customized CV Preview */}
                  <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xl font-semibold text-gray-900">
                        Customized CV
                      </h3>
                      <button
                        onClick={() => handleDownloadCV(selectedApp.id)}
                        className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Download CV (PDF)
                      </button>
                    </div>

                    {/* CV Preview Placeholder */}
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 bg-gray-50">
                      <div className="text-center">
                        <svg className="mx-auto h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <p className="mt-4 text-sm text-gray-600">
                          Your customized CV is ready for download
                        </p>
                        <p className="mt-2 text-xs text-gray-500">
                          Tailored to match the job requirements and company culture
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Cover Letter Preview */}
                  <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xl font-semibold text-gray-900">
                        Cover Letter
                      </h3>
                      <button
                        onClick={() => handleDownloadCoverLetter(selectedApp.id)}
                        className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                      >
                        <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Download Cover Letter
                      </button>
                    </div>

                    {/* Cover Letter Preview Placeholder */}
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 bg-gray-50">
                      <div className="text-center">
                        <svg className="mx-auto h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                        <p className="mt-4 text-sm text-gray-600">
                          Cover letter not generated for this job
                        </p>
                        <p className="mt-2 text-xs text-gray-500">
                          Generate a personalized cover letter to increase your chances
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Apply Now Button */}
                  <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-xl font-semibold text-gray-900 mb-4">
                      Ready to Apply?
                    </h3>
                    <div className="flex gap-4">
                      <button
                        onClick={() => handleApplyNow(selectedApp.job_url, selectedApp.id)}
                        className="flex-1 inline-flex items-center justify-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                      >
                        <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                        Apply Now
                      </button>
                      <button
                        onClick={() => router.push('/jobs/ai-matches')}
                        className="flex-1 inline-flex items-center justify-center px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
                      >
                        <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                        Apply to More Jobs
                      </button>
                    </div>
                    <p className="mt-4 text-sm text-gray-600">
                      Click "Apply Now" to open the job application page in a new tab, 
                      then upload your downloaded CV and cover letter.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}