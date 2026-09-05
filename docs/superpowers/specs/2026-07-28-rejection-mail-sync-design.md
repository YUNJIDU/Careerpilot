# Rejection Mail Sync Design

> 历史记录（2026-09-05 统一标记）：正文保留当时的设计、任务和验收假设，不是当前执行指令。冲突内容已由[当前规则](../../../plan/CURRENT-POLICY.md)替代；按总体规划与新验收核对差距，不重做已完成阶段。

## Goal

Recognize resume-screening rejection emails such as “暂时无法邀请你继续参与后续流程” and update the matching existing application to `已结束（简历未通过）`.

## Scope

- Extend the job-mail prefilter to admit resume-screening and rejection wording.
- Extend fact extraction to classify the supplied rejection wording as a resume-stage rejection.
- Keep the existing exact normalized company-and-role matching behavior.
- Keep differently ordered company names such as `蔚来NIO` and `NIO蔚来` as separate applications.
- Do not add alias management, automatic merging, or duplicate restoration.

## Data Flow

The mail remains read-only. A qualifying message passes the prefilter, produces rejection facts, links through the existing company-and-role matcher, and uses the existing authoritative mail reconciliation to update the stage and Excel export.

If the message does not provide enough identity information to match an application, it remains stored as unlinked mail rather than guessing.

## Verification

Add one regression test covering the supplied rejection wording and asserting:

- the message passes the job-mail prefilter;
- extraction returns `已结束（简历未通过）`;
- the resume field is marked `未通过`.

Run the focused Stage 3/4A tests.
