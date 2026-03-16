import { z } from "zod";

const looseObjectSchema = z.object({}).catchall(z.unknown());

export const persistedBetHistoryItemSchema = z
  .object({
    id: z.string(),
    evaluation_id: z.string().nullable().optional(),
    evaluationId: z.string().nullable().optional(),
    input_text: z.string(),
    inputText: z.string().nullable().optional(),
    status: z.string(),
    verdict: z.string().nullable().optional(),
    confidence: z.number().nullable().optional(),
    created_at: z.string(),
    createdAt: z.string().nullable().optional(),
  })
  .passthrough();

export const persistedBetHistoryResponseSchema = z
  .object({
    bets: z.array(persistedBetHistoryItemSchema),
    total: z.number(),
    page: z.number(),
    per_page: z.number(),
  })
  .passthrough();

export const replayBuilderHandoffSchema = z
  .object({
    evaluationId: z.string().nullable().optional(),
    inputText: z.string(),
    tier: z.string(),
    primaryFailure: looseObjectSchema.nullable().optional(),
    fastestFix: looseObjectSchema.nullable().optional(),
    deltaPreview: looseObjectSchema.nullable().optional(),
    signalInfo: looseObjectSchema.nullable().optional(),
    protocolContextNote: z.string().nullable().optional(),
  })
  .passthrough();

export const persistedBetReplaySchema = z
  .object({
    evaluationId: z.string().nullable().optional(),
    inputText: z.string(),
    tier: z.string(),
    builderHandoff: replayBuilderHandoffSchema.nullable().optional(),
    signalInfo: looseObjectSchema.nullable().optional(),
    primaryFailure: looseObjectSchema.nullable().optional(),
    triggeredProtocols: z.array(z.string()).default([]),
  })
  .passthrough();

export const persistedBetDetailSchema = z
  .object({
    id: z.string(),
    evaluation_id: z.string().nullable().optional(),
    evaluationId: z.string().nullable().optional(),
    input_text: z.string(),
    inputText: z.string().nullable().optional(),
    replay: persistedBetReplaySchema.nullable().optional(),
  })
  .passthrough();

export const evaluationHistoryItemSchema = z
  .object({
    id: z.string(),
    inputText: z.string(),
    signal: z.string().nullable().optional(),
    label: z.string().nullable().optional(),
    grade: z.string().nullable().optional(),
    fragilityScore: z.number().nullable().optional(),
  })
  .passthrough();

export const evaluationHistoryListResponseSchema = z
  .object({
    requestId: z.string(),
    items: z.array(evaluationHistoryItemSchema),
    count: z.number(),
  })
  .passthrough();

export const evaluationHistoryDetailResponseSchema = z
  .object({
    requestId: z.string(),
    item: looseObjectSchema,
  })
  .passthrough();

export type PersistedBetHistoryResponse = z.infer<typeof persistedBetHistoryResponseSchema>;
export type PersistedBetDetail = z.infer<typeof persistedBetDetailSchema>;
export type EvaluationHistoryListResponse = z.infer<typeof evaluationHistoryListResponseSchema>;
export type EvaluationHistoryDetailResponse = z.infer<typeof evaluationHistoryDetailResponseSchema>;
