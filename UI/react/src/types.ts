import type { ModelType } from "./config";

export interface NewsEntry {
  id: string;
  title: string;
  summary?: string;
  url?: string;
  source: string;
  model: ModelType;
}







