export async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export async function uploadAttachmentFile(tradeId, slot, file, notes = '') {
  const params = new URLSearchParams({ file_name: file.name });
  if (file.type) {
    params.set('content_type', file.type);
  }
  if (notes) {
    params.set('notes', notes);
  }

  const response = await fetch(`/trades/${tradeId}/attachments/${slot}/file?${params.toString()}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/octet-stream' },
    body: file,
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Upload failed: ${response.status}`);
  }

  return response.json();
}
