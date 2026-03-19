export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:5000";

export type ModelType = "llama";

export const MODEL_LABELS: Record<ModelType, string> = {
  llama: "Llama Özetleri"
};

export const MODEL_SEQUENCE: ModelType[] = ["llama"];
