export const API_URL: string =
  import.meta.env.CTRON_API_URL || "http://localhost:5001";

export const WEBSOCKET_ENGINE_URL: string =
  import.meta.env.CTRON_WEBSOCKET_ENGINE_URL|| "http://localhost:8100";
  
export const API_BASE_URL: string = 
  import.meta.env.CTRON_LLM_API_BASE_URL || 'http://localhost:8000';