# 05 — Frontend Plan (POC)

> Next.js frontend — what to build, component breakdown, integration.

---

## Owner: M2 (Frontend Lead)

---

## Setup (Day 1, first 30 min)

```bash
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir
cd frontend
npx shadcn@latest init
npx shadcn@latest add button card input textarea badge tabs separator progress alert
npm install axios lucide-react react-dropzone
```

**Environment:**
```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Page Layout (Single Page App)

```
┌────────────────────────────────────────────────────────────┐
│  🛰️ SatQuery AI                              [Health ●]  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────┐  ┌──────────────────────┐       │
│  │   IMAGE 1 (Required) │  │   IMAGE 2 (Optional) │       │
│  │   [Drop Zone]        │  │   [Drop Zone]        │       │
│  │   Modality: [▼]      │  │   Modality: [▼]      │       │
│  └──────────────────────┘  └──────────────────────┘       │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │  💬 Ask a question...                    [Analyze] │   │
│  └────────────────────────────────────────────────────┘   │
│  [VQA] [Describe] [Grounding] [Change] [Optical+SAR]      │
│                                                            │
│  ┌────────── RESULT ──────────────────────────────────┐   │
│  │  Answer text                    Confidence: 87%    │   │
│  │  Evidence images (change map, overlay, etc.)       │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  ┌────────── EXECUTION TRACE ─────────────────────────┐   │
│  │  ✅ Input: 2 images, GeoTIFF, Optical, Bi-temporal │   │
│  │  🎯 Task: CHANGE ANALYSIS (90%)                    │   │
│  │  🔧 Step 1: change_detection (1240ms) ✓            │   │
│  │  🔧 Step 2: rs_vlm (890ms) ✓                       │   │
│  │  ⏱️ Total: 2.13s                                   │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

---

## Components to Build

### Build Order:

| # | Component | When | Time Est |
|---|-----------|------|----------|
| 1 | `ImageUpload.tsx` | Day 1 Morning | 1 hour |
| 2 | `QueryInput.tsx` | Day 1 Morning | 30 min |
| 3 | `ResultPanel.tsx` | Day 1 Afternoon | 1 hour |
| 4 | `ExecutionTrace.tsx` | Day 1 Afternoon | 1 hour |
| 5 | `ConfidenceBadge.tsx` | Day 1 Afternoon | 15 min |
| 6 | `page.tsx` (main page) | Day 1 Evening | 1 hour |
| 7 | `useAnalysis.ts` (API hook) | Day 1 Evening | 30 min |
| 8 | Evidence images display | Day 2 Morning | 1 hour |
| 9 | Loading states + errors | Day 2 Afternoon | 1 hour |
| 10 | Polish + responsive | Day 3 Morning | 2 hours |

---

## Key Component Specs

### ImageUpload.tsx
- react-dropzone for drag & drop
- Accept: .tif, .tiff, .png, .jpg, .jpeg
- Show image preview (for PNG/JPEG; placeholder for TIFF)
- Modality dropdown: Optical / SAR
- Optional date input
- Remove button

### QueryInput.tsx
- Textarea for natural language query
- Example query badges (click to fill)
- Enter to submit (Shift+Enter for newline)
- Analyze button with loading spinner

### ResultPanel.tsx
- Answer text in a highlighted box
- Confidence badge (green > 80%, yellow > 60%, red < 60%)
- Evidence images grid (from backend URLs)
- Detected regions list with per-region confidence

### ExecutionTrace.tsx
- Collapsible card
- Input validation summary (badges for format, modality, etc.)
- Detected task with confidence
- Pipeline steps with status icons (✅/❌) and timing
- Total time

---

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
    images.forEach(img => form.append("images", img));
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

---

## Running

```bash
cd frontend
npm run dev
# → http://localhost:3000
```

---

## POC Simplifications

| Full Version | POC Version |
|-------------|-------------|
| OpenLayers satellite viewer | Simple `<img>` tags |
| Zustand state management | React useState |
| Download PDF report | Skip |
| Dark mode | Skip |
| Animations | Minimal (loading spinner only) |
| Responsive mobile | Desktop-only is fine |
