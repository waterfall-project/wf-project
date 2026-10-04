// Written by `make generate-client` from the examples of the contract: never edited by hand.

/**
 * The fixtures of `fixtures/api/` the contract cites as examples, by operation and status: what
 * the fake client of the tests may answer to each (`src/test/fixtures.ts`).
 */
export interface Examples {
  "DELETE /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}": {
    200: "node_deleted";
  };
  "GET /installation": {
    200: "installation" | "installation_english";
  };
  "GET /me": {
    200: "me" | "me_directory" | "me_english" | "me_with_avatar" | "me_without_preferences";
  };
  "GET /portfolio/pilot-health": {
    200: "pilot_health";
  };
  "GET /portfolio/projects": {
    200: "volume/portfolio_projects";
  };
  "GET /projects": {
    200: "projects" | "projects_empty";
  };
  "GET /projects/{project_id}": {
    200: "project" | "project_pricing";
  };
  "GET /projects/{project_id}/contributors": {
    200: "contributors";
  };
  "GET /projects/{project_id}/estimate-indicators": {
    200: "estimate_indicators" | "estimate_indicators_breakdown" | "estimate_indicators_missing_rates" | "volume/estimate_indicators";
  };
  "GET /projects/{project_id}/estimate-indicators/missing-rates": {
    200: "missing_rates" | "missing_rates_none";
  };
  "GET /projects/{project_id}/indicators": {
    200: "project_indicators";
  };
  "GET /projects/{project_id}/indicators/cost-curve": {
    200: "cost_curve" | "cost_curve_amendment" | "cost_curve_payment_delays";
  };
  "GET /projects/{project_id}/indicators/earned-value-curves": {
    200: "earned_value_curves";
  };
  "GET /projects/{project_id}/indicators/index-history": {
    200: "index_history";
  };
  "GET /projects/{project_id}/indicators/milestone-tracking": {
    200: "milestone_tracking" | "milestone_tracking_none";
  };
  "GET /projects/{project_id}/remaining-indicators": {
    200: "remaining_indicators" | "remaining_indicators_over_budget";
  };
  "GET /projects/{project_id}/revisions": {
    200: "revisions" | "revisions_empty";
  };
  "GET /projects/{project_id}/revisions/comparison": {
    200: "comparison" | "comparison_identical";
  };
  "GET /projects/{project_id}/revisions/{revision_id}": {
    200: "revision" | "revision_estimator" | "revision_marked" | "revision_marking" | "revision_reader";
  };
  "GET /projects/{project_id}/revisions/{revision_id}/rate-update": {
    200: "rate_update" | "rate_update_none";
  };
  "GET /projects/{project_id}/revisions/{revision_id}/structures": {
    200: "structures" | "structures_amendments";
  };
  "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes": {
    200: "nodes" | "nodes_estimate" | "nodes_milestone" | "nodes_planning" | "nodes_risk_occurred" | "volume/nodes_thousand";
  };
  "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/dependencies": {
    200: "dependencies_labour" | "dependencies_manual_float" | "dependencies_provision" | "dependencies_summary" | "dependencies_summary_moved" | "dependencies_task_amount" | "volume/summary_dependencies";
  };
  "GET /projects/{project_id}/risks": {
    200: "risks" | "risks_empty";
  };
  "GET /projects/{project_id}/risks/matrix": {
    200: "risk_matrix";
  };
  "GET /projects/{project_id}/risks/{risk_id}": {
    200: "risk" | "risk_occurred_detail";
  };
  "GET /projects/{project_id}/risks/{risk_id}/reviews": {
    200: "risk_reviews";
  };
  "GET /projects/{project_id}/state-transitions": {
    200: "state_transitions" | "state_transitions_exited";
  };
  "GET /projects/{project_id}/subprojects": {
    200: "subprojects";
  };
  "GET /reference/cost-categories": {
    200: "volume/cost_categories";
  };
  "GET /reference/cost-categories/{cost_category_id}/hourly-rates": {
    200: "volume/hourly_rates";
  };
  "GET /reference/duration-units": {
    200: "duration_units";
  };
  "GET /reference/hourly-rates": {
    200: "volume/hourly_rate_grid";
  };
  "GET /reference/readiness": {
    200: "reference_readiness" | "reference_readiness_incomplete";
  };
  "GET /reference/resource-roles": {
    200: "resource_roles";
  };
  "GET /session": {
    200: "session" | "session_dark" | "session_english" | "session_estimator" | "session_grid_settings" | "session_without_administration" | "session_without_preferences";
  };
  "GET /session/providers": {
    200: "auth_providers" | "auth_providers_local";
  };
  "GET /tasks": {
    200: "tasks_none" | "tasks_running";
  };
  "GET /tasks/{task_id}": {
    200: "task_failed" | "task_import_succeeded" | "task_mark_relaunched" | "task_running" | "task_succeeded";
  };
  "PATCH /me/preferences": {
    200: "preferences" | "preferences_dark";
  };
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line": {
    200: "estimate_line_entered" | "estimate_line_updated";
  };
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task": {
    200: "task_renamed";
  };
  "POST /projects/{project_id}/exit": {
    200: "project_completed";
  };
  "POST /projects/{project_id}/imports/{import_id}/apply": {
    202: "task_import_queued";
  };
  "POST /projects/{project_id}/revisions/{revision_id}/mark": {
    202: "task_mark_queued" | "task_mark_relaunched";
  };
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste": {
    200: "paste_applied";
  };
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste-preview": {
    200: "paste_plan" | "paste_plan_unknown_category";
  };
  "POST /session": {
    201: "session";
  };
  "PUT /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/predecessors": {
    200: "predecessor_set";
  };
}
