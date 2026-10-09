// Written by `make generate-client` from the examples of the contract: never edited by hand.

/**
 * The fixtures of `fixtures/api/` the contract cites as examples, by operation and status: what
 * the fake client of the tests may answer to each (`src/test/fixtures.ts`).
 */
export interface Examples {
  "DELETE /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}": {
    200: "node_deleted";
  };
  "GET /access-roles": {
    200: "access_roles";
  };
  "GET /audit-events": {
    200: "audit_events" | "audit_events_by_actor" | "audit_events_by_object_label" | "audit_events_correlation" | "audit_events_empty" | "audit_events_exited" | "audit_events_import_applied" | "audit_events_page" | "audit_events_project" | "audit_events_search";
  };
  "GET /audit-events/facets": {
    200: "audit_facets";
  };
  "GET /backup-schedule": {
    200: "backup_schedule" | "backup_schedule_disabled" | "backup_schedule_weekly";
  };
  "GET /backups": {
    200: "backups" | "backups_beyond" | "backups_empty";
  };
  "GET /external-backup-locations": {
    200: "external_backup_locations" | "external_backup_locations_none";
  };
  "GET /installation": {
    200: "installation" | "installation_english";
  };
  "GET /me": {
    200: "me" | "me_directory" | "me_english" | "me_with_avatar" | "me_without_preferences";
  };
  "GET /permissions": {
    200: "permissions";
  };
  "GET /portfolio/cost-curve": {
    200: "portfolio_cost_curve" | "portfolio_cost_curve_credit" | "portfolio_cost_curve_payment_delays";
  };
  "GET /portfolio/cost-structure": {
    200: "volume/portfolio_cost_structure";
  };
  "GET /portfolio/performance": {
    200: "volume/portfolio_performance";
  };
  "GET /portfolio/pilot-health": {
    200: "pilot_health";
  };
  "GET /portfolio/projects": {
    200: "portfolio_projects_empty" | "volume/portfolio_projects" | "volume/portfolio_projects_page";
  };
  "GET /portfolio/risks": {
    200: "volume/portfolio_risks";
  };
  "GET /portfolio/value": {
    200: "volume/portfolio_value";
  };
  "GET /portfolio/workload": {
    200: "portfolio_workload" | "portfolio_workload_org_node";
  };
  "GET /projects": {
    200: "projects" | "projects_default_states" | "projects_empty" | "projects_period" | "projects_search_code";
  };
  "GET /projects/{project_id}": {
    200: "project" | "project_pricing" | "project_pricing_estimator" | "project_reader" | "project_without_current_revision";
  };
  "GET /projects/{project_id}/actual-costs": {
    200: "actual_costs" | "actual_costs_after_exclusion" | "actual_costs_empty" | "actual_costs_page" | "actual_costs_subproject";
  };
  "GET /projects/{project_id}/contributors": {
    200: "contributors" | "contributors_by_name" | "contributors_inactive" | "contributors_search";
  };
  "GET /projects/{project_id}/cost-imports": {
    200: "cost_imports" | "cost_imports_beyond" | "cost_imports_empty";
  };
  "GET /projects/{project_id}/estimate-indicators": {
    200: "estimate_indicators" | "estimate_indicators_breakdown" | "estimate_indicators_missing_rates" | "volume/estimate_indicators_volume";
  };
  "GET /projects/{project_id}/estimate-indicators/missing-rates": {
    200: "missing_rates" | "missing_rates_none";
  };
  "GET /projects/{project_id}/imports": {
    200: "imports" | "imports_empty" | "imports_page";
  };
  "GET /projects/{project_id}/imports/{import_id}": {
    200: "import_actual_costs_analysed" | "import_analysed" | "import_analysing" | "import_planning_mismatch" | "import_remaining_analysed";
  };
  "GET /projects/{project_id}/indicators": {
    200: "project_indicators" | "project_indicators_marked";
  };
  "GET /projects/{project_id}/indicators/cost-curve": {
    200: "cost_curve" | "cost_curve_amendment" | "cost_curve_payment_delays" | "cost_curve_subproject" | "cost_curve_subproject_empty" | "cost_curve_subproject_empty_payment_delays" | "cost_curve_subproject_unbudgeted";
  };
  "GET /projects/{project_id}/indicators/earned-value-curves": {
    200: "earned_value_curves";
  };
  "GET /projects/{project_id}/indicators/index-history": {
    200: "index_history" | "index_history_subproject";
  };
  "GET /projects/{project_id}/indicators/milestone-tracking": {
    200: "milestone_tracking" | "milestone_tracking_none";
  };
  "GET /projects/{project_id}/remaining-indicators": {
    200: "remaining_indicators" | "remaining_indicators_over_budget";
  };
  "GET /projects/{project_id}/remaining-indicators/startable-tasks": {
    200: "startable_tasks" | "startable_tasks_milestone";
  };
  "GET /projects/{project_id}/revisions": {
    200: "revisions" | "revisions_empty" | "revisions_marked";
  };
  "GET /projects/{project_id}/revisions/comparison": {
    200: "comparison" | "comparison_identical";
  };
  "GET /projects/{project_id}/revisions/{revision_id}": {
    200: "revision" | "revision_estimator" | "revision_importing" | "revision_marked" | "revision_marking" | "revision_offer" | "revision_reader";
  };
  "GET /projects/{project_id}/revisions/{revision_id}/rate-update": {
    200: "rate_update" | "rate_update_none";
  };
  "GET /projects/{project_id}/revisions/{revision_id}/structures": {
    200: "structures" | "structures_amendments";
  };
  "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes": {
    200: "nodes" | "nodes_core" | "nodes_estimate" | "nodes_estimate_hours" | "nodes_estimate_sorted" | "nodes_installation" | "nodes_milestone" | "nodes_nested" | "nodes_planning" | "nodes_risk_occurred" | "nodes_summaries" | "nodes_summaries_leaves" | "nodes_timeline" | "volume/nodes_thousand";
  };
  "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/dependencies": {
    200: "dependencies_labour" | "dependencies_manual_float" | "dependencies_provision" | "dependencies_summary" | "dependencies_summary_moved" | "dependencies_task_amount" | "volume/summary_dependencies";
  };
  "GET /projects/{project_id}/risks": {
    200: "risks" | "risks_empty";
  };
  "GET /projects/{project_id}/risks/coverage": {
    200: "risk_coverage";
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
    200: "subprojects" | "subprojects_by_label" | "subprojects_with_actual_costs";
  };
  "GET /projects/{project_id}/timelines": {
    200: "timelines" | "timelines_empty";
  };
  "GET /projects/{project_id}/work-breakdown": {
    200: "work_breakdown" | "work_breakdown_default";
  };
  "GET /projects/{project_id}/workload": {
    200: "workload" | "workload_marked_remaining" | "workload_org_node" | "workload_reference_budget";
  };
  "GET /reference/calendars": {
    200: "calendars" | "calendars_reader" | "calendars_with_inactive";
  };
  "GET /reference/cost-categories": {
    200: "volume/cost_categories" | "volume/cost_categories_page" | "volume/cost_categories_reader";
  };
  "GET /reference/cost-categories/{cost_category_id}/hourly-rates": {
    200: "volume/hourly_rates";
  };
  "GET /reference/cost-types": {
    200: "cost_types" | "cost_types_reader";
  };
  "GET /reference/duration-units": {
    200: "duration_units";
  };
  "GET /reference/hourly-rates": {
    200: "volume/hourly_rate_grid" | "volume/hourly_rate_grid_bounded" | "volume/hourly_rate_grid_by_rate";
  };
  "GET /reference/org-nodes": {
    200: "org_nodes" | "org_nodes_reader" | "org_nodes_with_inactive";
  };
  "GET /reference/readiness": {
    200: "reference_readiness" | "reference_readiness_incomplete";
  };
  "GET /reference/resource-roles": {
    200: "resource_roles" | "resource_roles_bounded" | "resource_roles_reader";
  };
  "GET /reference/settings": {
    200: "reference_settings";
  };
  "GET /session": {
    200: "session" | "session_auditor" | "session_dark" | "session_english" | "session_estimator" | "session_grid_settings" | "session_manager" | "session_without_administration" | "session_without_preferences" | "session_without_roles";
  };
  "GET /session/providers": {
    200: "auth_providers" | "auth_providers_local";
  };
  "GET /system/status": {
    200: "system_status" | "system_status_backup_failed" | "system_status_copy_failed" | "system_status_storage_full";
  };
  "GET /tasks": {
    200: "tasks_none" | "tasks_running";
  };
  "GET /tasks/{task_id}": {
    200: "task_export_succeeded" | "task_failed" | "task_import_succeeded" | "task_mark_relaunched" | "task_running" | "task_succeeded";
  };
  "GET /users": {
    200: "users" | "users_page";
  };
  "PATCH /me/preferences": {
    200: "preferences" | "preferences_dark";
  };
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line": {
    200: "estimate_line_entered" | "estimate_line_redated" | "estimate_line_updated";
  };
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task": {
    200: "task_renamed" | "volume/task_lengthened";
  };
  "POST /external-backup-locations/{location_name}/test": {
    200: "external_backup_location_test_failed" | "external_backup_location_tested";
  };
  "POST /file-uploads": {
    201: "file_upload";
  };
  "POST /projects/{project_id}/exit": {
    200: "project_completed";
  };
  "POST /projects/{project_id}/exports": {
    202: "task_export_queued";
  };
  "POST /projects/{project_id}/imports": {
    202: "import_analysing";
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
  "PUT /projects/{project_id}/actual-costs/{cost_line_id}/tracked-scope": {
    200: "actual_cost_excluded" | "actual_cost_reinstated";
  };
  "PUT /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/predecessors": {
    200: "predecessor_set";
  };
  "PUT /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/remaining": {
    200: "remaining_reestimated";
  };
  "PUT /reference/cost-categories/{cost_category_id}/hourly-rates/{year}": {
    200: "hourly_rate_added_year" | "hourly_rate_corrected" | "hourly_rate_entered";
  };
  "PUT /reference/org-nodes/{org_node_id}/activation": {
    200: "org_node_reactivated";
  };
  "PUT /reference/resource-roles/{resource_role_id}/activation": {
    200: "resource_role_reactivated";
  };
}
