# 05 — Frontend Plan (POC)

> Frontend architecture, interaction flow, and the component structure needed to deliver a polished demo experience.

## Owner: M2 (Frontend Lead)

## Setup

```bash
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir
cd frontend
npx shadcn@latest init
npx shadcn@latest add button card input textarea badge tabs separator progress alert
npm install axios lucide-react react-dropzone
```

Environment:

```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Page Layout

```text
┌────────────────────────────────────────────────────────────┐
│ SatQuery AI                                      [Health] │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────┐  ┌──────────────────────┐      │
│  │ Image 1 (Required)   │  │ Image 2 (Optional)    │      │
│  │ Drop zone            │  │ Drop zone            │      │
│  │ Modality: Optical    │  │ Modality: Optical    │      │
│  └──────────────────────┘  └──────────────────────┘      │
│                                                            │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Ask a question...                     [Analyze]   │    │
│  └────────────────────────────────────────────────────┘    │
│  [VQA] [Describe] [Grounding] [Change] [Optical + SAR]    │
│                                                            │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Result panel                                        │    │
│  │ Answer text                                87%     │    │
│  │ Evidence images and highlighted regions             │    │
│  └────────────────────────────────────────────────────┘    │
│                                                            │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Execution Trace                                     │    │
│  │ Input validated: 2 images, GeoTIFF, optical         │    │
│  │ Task: change analysis (90%)                          │    │
│  │ Step 1: change_detection (1240ms)                    │    │
│  │ Step 2: rs_vlm (890ms)                               │    │
│  │ Total: 2.13s                                         │    │
│  └────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────┘
```

## Component Breakdown

| # | Component | Timing | Purpose |
|---|---|---|---|
| 1 | `ImageUpload.tsx` | Day 1 morning | drag-and-drop input and preview |
| 2 | `QueryInput.tsx` | Day 1 morning | natural-language input and example prompts |
| 3 | `ResultPanel.tsx` | Day 1 afternoon | answer, confidence, and evidence section |
| 4 | `ExecutionTrace.tsx` | Day 1 afternoon | trace visualization and pipeline summary |
| 5 | `ConfidenceBadge.tsx` | Day 1 afternoon | confidence display |
| 6 | `page.tsx` | Day 1 evening | main dashboard composition |
| 7 | `useAnalysis.ts` | Day 1 evening | API integration and request state |
| 8 | Evidence image display | Day 2 morning | render backend outputs cleanly |
| 9 | Loading and error states | Day 2 afternoon | improve feedback and resilience |
| 10 | Final polish | Day 3 morning | responsive layout and visual finish |

## Key Component Specifications

### `ImageUpload.tsx`

- drag-and-drop file upload
- accepted formats: `.tif`, `.tiff`, `.png`, `.jpg`, `.jpeg`
- preview for PNG/JPEG inputs and placeholder handling for TIFF
- modality selector for optical vs SAR
- optional date field
- remove/reset action

### `QueryInput.tsx`

- textarea for natural-language prompts
- clickable example prompts
- submit action with loading states
- support for multi-line entry where needed

### `ResultPanel.tsx`

- answer text in a structured summary block
- confidence indicator with thresholds for low, medium, and high certainty
- evidence image grid from backend response
- list of detected regions with per-region confidence

### `ExecutionTrace.tsx`

- collapsible trace card
- validation summary for format, modality, and image count
- detected task and confidence
- list of pipeline steps with timing and status
- cumulative execution time

## API Integration

```typescript
// src/hooks/useAnalysis.ts
import { useState } from "react";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useAnalysis() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = async (images: File[], query: string, modalities: string[]) => {
    setLoading(true);
    setError(null);
    setResult(null);

    const form = new FormData();
    images.forEach((img) => form.append("images", img));
    form.append("query", query);
    form.append("modalities", modalities.join(","));

    try {
      const res = await axios.post(`${API}/api/analyze`, form, { timeout: 120000 });
      setResult(res.data);
    } catch (e: any) {
      setError(e.response?.data?.detail?.errors?.join(", ") || e.message);
    } finally {
      setLoading(false);
    }
  };

  return { analyze, result, loading, error };
}
```

## Running the Frontend

```bash
cd frontend
npm run dev
```

Open http://localhost:3000 in the browser.

## POC Simplifications

| Full version | POC version |
|---|---|
| OpenLayers-based viewer | simple image tags |
| Zustand state management | React `useState` |
| PDF export | omitted |
| advanced dark mode styling | minimal visual polish |
| complex animations | loading state only |
| mobile-first responsiveness | desktop-focused demo |
