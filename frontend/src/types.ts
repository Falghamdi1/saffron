export interface MenuItem {
  id: string;
  name: string;
  category: "starter" | "main" | "dessert" | "drink";
  cuisine: string;
  price: number;
  spice_level: number;
  description: string;
  ingredients: string[];
  allergens: string[];
  may_contain: string[];
  diets: string[];
  available: boolean;
  allergen_info_complete: boolean;
}

export type MenuEntry = MenuItem & { violations: string[] };

export interface Recommendation {
  item: MenuItem;
  reasons: string[];
  cautions: string[];
}

export interface MemoryNote {
  kind: "saved" | "updated" | "removed" | "needs_confirmation" | "conflict" | "temporary";
  message: string;
  preference_id: string | null;
}

export interface MessagePayload {
  recommendations?: Recommendation[];
  comparison?: { item: MenuItem; violations: string[] }[];
  memory_notes?: MemoryNote[];
  notice?: string;
  engine?: string;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  payload: MessagePayload;
}

export interface Conversation {
  id: string;
  title: string;
  updated_at: string;
}

export interface Preference {
  id: string;
  category: string;
  value: string;
  status: "active" | "pending";
  certainty: "confirmed" | "inferred";
  removal_requested: boolean;
  source_text: string;
  updated_at: string;
}

export interface MemoryEvent {
  id: number;
  event_type: string;
  category: string;
  value: string;
  reason: string;
  source_text: string;
  created_at: string;
}

export interface Memory {
  preferences: Preference[];
  history: MemoryEvent[];
}

export type MemoryAction = "confirm" | "dismiss" | "forget";

export interface AppConfig {
  auth_mode: "local" | "supabase";
  supabase_url: string;
  supabase_anon_key: string;
  language_model: boolean;
}
