"use client";

import { useMutation } from "@tanstack/react-query";
import { ChangeEvent, useState } from "react";

import { DevConsoleShell } from "@/components/dev-console-shell";
import { DevPageHeader } from "@/components/dev-page-header";
import { DevRouteOps } from "@/components/dev-route-ops";
import { EvaluationEnvelopeView } from "@/components/evaluation-envelope-view";
import { postOcrReview } from "@/lib/api/ocr-review";
import { createEnvelopeFromOcrReview } from "@/lib/adapters/evaluation-envelope";
import { ocrReviewEnvelopeMock } from "@/lib/mocks/evaluation-envelope";
import { useDevMode } from "@/lib/use-dev-mode";

export function OcrReviewShell() {
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const { mode, setMode } = useDevMode();

  const ocrMutation = useMutation({
    mutationFn: postOcrReview,
  });

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      setSelectedFileName(null);
      return;
    }

    setSelectedFileName(file.name);
    ocrMutation.mutate(file);
  }

  const result = ocrMutation.data;
  const envelope = mode === "mock" ? ocrReviewEnvelopeMock : result ? createEnvelopeFromOcrReview(result) : null;
  const trace =
    mode === "mock"
      ? {
          label: "Fixture-driven OCR review preview",
          status: "mock" as const,
          detail: "Rendering the OCR review fixture without uploading an image.",
          endpoint: "/api/ocr/review",
          method: "POST",
          lastEvent: "Mock OCR envelope loaded.",
        }
      : ocrMutation.isPending
        ? {
            label: "OCR review request in flight",
            status: "pending" as const,
            detail: selectedFileName ? `Uploading ${selectedFileName} for OCR review.` : "Uploading selected image for OCR review.",
            endpoint: "/api/ocr/review",
            method: "POST",
            lastEvent: "Waiting for OCR extraction response.",
          }
        : ocrMutation.isError
          ? {
              label: "OCR review failed",
              status: "error" as const,
              detail: (ocrMutation.error as Error).message || "OCR review request failed.",
              endpoint: "/api/ocr/review",
              method: "POST",
              lastEvent: "Latest OCR review attempt returned an error.",
            }
          : result
            ? {
                label: "OCR review response ready",
                status: "success" as const,
                detail: `Review ${result.requestId} returned ${result.detectedLegs.length} detected leg(s).`,
                endpoint: "/api/ocr/review",
                method: "POST",
                lastEvent: "Latest OCR review response normalized into an envelope.",
              }
            : {
                label: "OCR review route idle",
                status: "idle" as const,
                detail: "Choose an image or switch to mock mode to inspect the review contract.",
                endpoint: "/api/ocr/review",
                method: "POST",
                lastEvent: "No OCR review request has been sent yet.",
              };

  return (
    <DevConsoleShell
      title="OCR review terminal"
      subtitle="Inspect OCR extraction, trust-gate signals, and the normalized review envelope before Evaluate."
      routeState={{ status: trace.status, label: trace.label }}
    >
      <DevPageHeader
        stage="Stage 2"
        title="Review before Evaluate"
        description="This screen stops at OCR review so frontend correction stays separate from evaluation."
        facts={[
          { label: "Route", value: <code>/evaluate/review</code> },
          { label: "Contract", value: <code>POST /api/ocr/review</code> },
          { label: "Output", value: <code>rawText + detectedLegs + requiresReview</code> },
        ]}
      />

      <section className="panel-grid">
        <div className="panel-stack">
        <DevRouteOps
          routeLabel={<code>/evaluate/review</code>}
          contractLabel={<code>POST /api/ocr/review</code>}
          mode={mode}
          onModeChange={setMode}
          trace={trace}
        />

        <section className="panel">
          <div className="panel-header">
            <h2>Upload image</h2>
            <span>Contract: POST /api/ocr/review</span>
          </div>

          <label className="upload-zone" htmlFor="ocr-file">
            <span>{selectedFileName || "Choose a slip screenshot"}</span>
            <input
              id="ocr-file"
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              className="sr-only"
              disabled={mode === "mock"}
            />
          </label>

          {ocrMutation.isPending ? <p className="status">Extracting OCR review payload...</p> : null}
          {ocrMutation.isError ? (
            <p className="status error">
              {(ocrMutation.error as Error).message || "OCR request failed"}
            </p>
          ) : null}
        </section>
        </div>

        <section className="panel result-panel">
          <div className="panel-header">
            <h2>EvaluationEnvelope view</h2>
            <span>OCR normalization layer</span>
          </div>

          {!result ? (
            <EvaluationEnvelopeView
              envelope={envelope}
              emptyMessage="Upload an image to inspect the normalized OCR envelope."
            />
          ) : (
            <>
              <dl className="summary-grid">
                <div>
                  <dt>requestId</dt>
                  <dd>{result.requestId}</dd>
                </div>
                <div>
                  <dt>Confidence</dt>
                  <dd>{Math.round(result.confidence * 100)}%</dd>
                </div>
                <div>
                  <dt>Requires review</dt>
                  <dd>{result.requiresReview ? "yes" : "no"}</dd>
                </div>
                <div>
                  <dt>Detected legs</dt>
                  <dd>{result.detectedLegs.length}</dd>
                </div>
              </dl>

              <div className="result-block">
                <h3>5-zone envelope</h3>
                <EvaluationEnvelopeView
                  envelope={envelope}
                  emptyMessage="Upload an image to inspect the normalized OCR envelope."
                />
              </div>
            </>
          )}
        </section>
      </section>
    </DevConsoleShell>
  );
}
