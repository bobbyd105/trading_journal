export const emptyReview = {
  review_status: 'not_started',
  summary: '',
  setup_quality_score: '',
  entry_quality_score: '',
  exit_quality_score: '',
  risk_management_score: '',
  discipline_score: '',
  followed_playbook: 'not_applicable',
  what_went_well: '',
  what_to_improve: '',
  lesson_learned: '',
  reviewed_at: '',
};

const scoreFields = [
  'setup_quality_score',
  'entry_quality_score',
  'exit_quality_score',
  'risk_management_score',
  'discipline_score',
];

export function reviewToForm(review) {
  if (!review) {
    return emptyReview;
  }
  return Object.fromEntries(
    Object.entries(emptyReview).map(([key, fallback]) => [key, review[key] ?? fallback]),
  );
}

export function toReviewPayload(form) {
  const payload = { ...form };
  scoreFields.forEach((field) => {
    payload[field] = payload[field] === '' ? null : Number(payload[field]);
  });
  ['summary', 'what_went_well', 'what_to_improve', 'lesson_learned', 'reviewed_at'].forEach((field) => {
    payload[field] = payload[field]?.trim() || null;
  });
  return payload;
}
