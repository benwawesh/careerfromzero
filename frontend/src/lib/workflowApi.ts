/**
 * API functions for Job Application Workflow
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';

export interface MatchJobRequest {
  cv_id: string;
  filters?: {
    location?: string;
    job_type?: string;
    experience_level?: string;
    min_salary?: number;
  };
  limit?: number;
  min_score?: number;
}

export interface BatchCustomizeRequest {
  cv_id: string;
  job_ids: string[];
  options?: {
    generate_cv?: boolean;
    generate_cover_letter?: boolean;
    save_as_drafts?: boolean;
  };
}

export interface CreateBatchRequest {
  cv_id: string;
  job_ids: string[];
  customizations: any[];
}

/**
 * Analyze user's CV
 */
export async function analyzeCV(cvId: string) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE_URL}/api/workflow/analyze-cv/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ cv_id: cvId }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to analyze CV');
  }

  return response.json();
}

/**
 * Find jobs matching user's CV
 */
export async function matchJobs(request: MatchJobRequest) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE_URL}/api/workflow/match-jobs/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to match jobs');
  }

  return response.json();
}

/**
 * Generate customizations for selected jobs
 */
export async function batchCustomize(request: BatchCustomizeRequest) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE_URL}/api/workflow/batch-customize/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to generate customizations');
  }

  return response.json();
}

/**
 * Create application batch for approval
 */
export async function createApplicationBatch(request: CreateBatchRequest) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE_URL}/api/workflow/create-batch/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to create application batch');
  }

  return response.json();
}

/**
 * Get current workflow progress
 */
export async function getProgress() {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE_URL}/api/workflow/progress/`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to get progress');
  }

  return response.json();
}

/**
 * List user's applications
 */
export async function listApplications(filters?: { status?: string; company?: string }) {
  const token = localStorage.getItem('access_token');
  
  const params = new URLSearchParams();
  if (filters?.status) params.append('status', filters.status);
  if (filters?.company) params.append('company', filters.company);
  
  const response = await fetch(`${API_BASE_URL}/api/workflow/applications/?${params}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to list applications');
  }

  return response.json();
}

/**
 * Get application details
 */
export async function getApplication(applicationId: string) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE_URL}/api/workflow/applications/${applicationId}/`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to get application');
  }

  return response.json();
}

/**
 * Update application
 */
export async function updateApplication(applicationId: string, data: any) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE_URL}/api/workflow/applications/${applicationId}/update/`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to update application');
  }

  return response.json();
}

/**
 * List application batches
 */
export async function listBatches() {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE_URL}/api/workflow/batches/`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to list batches');
  }

  return response.json();
}

/**
 * Get batch details
 */
export async function getBatch(batchId: string) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE_URL}/api/workflow/batches/${batchId}/`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to get batch');
  }

  return response.json();
}

/**
 * Approve or reject batch item
 */
export async function approveBatchItem(batchId: string, itemId: string, approve: boolean) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE_URL}/api/workflow/batches/${batchId}/items/${itemId}/approve/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ approve }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to approve item');
  }

  return response.json();
}