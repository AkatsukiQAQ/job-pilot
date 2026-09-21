// Mirrors src/jobpilot/web/schemas.py. Enum string values match jobpilot/domain.py.

export type Status =
  | 'unrecorded' | 'considering' | 'preparing'
  | 'applied' | 'assessment' | 'interviewing'
  | 'offer' | 'accepted' | 'joined'
  | 'unsuitable' | 'withdrawn' | 'rejected';

export type Track = 'intern' | 'newgrad' | 'midcareer' | 'other';
export type Kind = 'newgrad' | 'midcareer' | 'intern' | 'other';
export type Source = 'gmail' | 'gcal' | 'linkedin_export' | 'chat' | 'manual' | 'import' | 'system';
export type EventType =
  | 'entry' | 'es_submitted' | 'document_screening' | 'ack' | 'viewed'
  | 'casual_interview' | 'web_test' | 'assessment' | 'interview' | 'final_interview' | 'scheduling'
  | 'pass' | 'rejection' | 'offer_informal' | 'offer' | 'offer_meeting' | 'accepted'
  | 'resignation_negotiation' | 'joined' | 'withdrawn'
  | 'portal_check_required' | 'followup_needed' | 'note';

export interface Meta {
  statuses: Status[];
  event_types: EventType[];
  tracks: Track[];
  kinds: Kind[];
  region_packs: string[];
  tz: string;
}

export interface Campaign {
  campaign_id: number;
  name: string;
  kind: Kind;
  region_pack: string;
  starts_on: string | null;
  ends_on: string | null;
  is_active: boolean;
  application_count: number;
  tz: string;
}

export interface CampaignIn {
  name: string;
  kind: Kind;
  region_pack: string;
  starts_on?: string | null;
  ends_on?: string | null;
}

export interface ApplicationRow {
  application_id: number;
  campaign_id: number;
  company: string;
  role: string | null;
  track: Track;
  auto_status: Status;
  user_status: Status | null;
  status: Status;
  origin: 'auto' | 'manual' | 'import';
  last_event_at: string | null;
  last_event_type: EventType | null;
  next_action: string | null;
  next_action_due: string | null;
  deadline_at: string | null;
  job_url: string | null;
  is_ghosted: boolean;
}

export interface EventIn {
  event_type: EventType;
  occurred_at: string;
  summary: string | null;
}

export interface EventOut {
  event_id: number;
  event_type: EventType;
  occurred_at: string;
  source: Source;
  summary: string | null;
  confidence: number;
  user_confirmed: boolean;
}

export interface ApplicationDetail extends ApplicationRow {
  notes: string | null;
  portal_url: string | null;
  applied_at: string | null;
  excluded_reason: string | null;
  created_at: string;
  events: EventOut[];
}

export interface ApplicationIn {
  campaign_id: number;
  company_name: string;
  role?: string | null;
  track: Track;
  job_url?: string | null;
  notes?: string | null;
  initial_status?: Status | null;
}

export interface ApplicationPatch {
  company_name: string;
  role: string | null;
  track: Track;
  job_url: string | null;
  notes: string | null;
  portal_url: string | null;
  deadline_at: string | null;
  next_action: string | null;
  next_action_due: string | null;
}

export interface DeleteOut {
  deleted_events: number;
}

export interface CampaignDeleteOut {
  deleted_applications: number;
  deleted_events: number;
}

export interface UpcomingItem {
  application_id: number;
  company: string;
  role: string | null;
  kind: 'deadline' | 'next_action';
  due: string;
  label: string | null;
  overdue: boolean;
}

export interface RecentEvent {
  event_id: number;
  application_id: number;
  company: string;
  event_type: EventType;
  occurred_at: string;
  summary: string | null;
}

export interface Dashboard {
  counts_by_status: Partial<Record<Status, number>>;
  upcoming: UpcomingItem[];
  recent_events: RecentEvent[];
  deadlines_this_week: number;
  interviews_next_7d: number;
}
