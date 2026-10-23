// Written by `make generate-client` from the examples of the contract: never edited by hand.

/**
 * The fixtures of `fixtures/api/` the contract cites as examples, by operation and status: what
 * the fake client of the tests may answer to each (`src/test/fixtures.ts`).
 */
export interface Examples {
  "DELETE /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}": {
    200: "node_deleted" | "node_summary_deleted";
  };
  "GET /access-roles": {
    200: "access_roles" | "access_roles_by_updated_by" | "access_roles_composed" | "access_roles_unheld" | "access_roles_updated_by_anonymized" | "access_roles_updated_by_deactivated";
  };
  "GET /audit-events": {
    200: "audit_events" | "audit_events_administration" | "audit_events_anonymized_actor" | "audit_events_anonymized_object" | "audit_events_by_actor" | "audit_events_by_object_label" | "audit_events_correlation" | "audit_events_empty" | "audit_events_exited" | "audit_events_import_applied" | "audit_events_page" | "audit_events_project" | "audit_events_search";
  };
  "GET /audit-events/facets": {
    200: "audit_facets" | "audit_facets_anonymized";
  };
  "GET /backup-schedule": {
    200: "backup_schedule" | "backup_schedule_disabled" | "backup_schedule_weekly";
  };
  "GET /backups": {
    200: "backups" | "backups_beyond" | "backups_by_size" | "backups_during_backup" | "backups_empty" | "backups_manual" | "backups_period" | "backups_reader" | "backups_retained" | "backups_unverified";
  };
  "GET /backups/{backup_id}": {
    200: "backup" | "backup_pending";
  };
  "GET /external-backup-locations": {
    200: "external_backup_locations" | "external_backup_locations_none";
  };
  "GET /health": {
    200: "liveness" | "liveness_maintenance";
  };
  "GET /identity-syncs/latest": {
    200: "identity_sync_report" | "identity_sync_report_anonymized" | "identity_sync_report_flagged";
  };
  "GET /installation": {
    200: "installation" | "installation_english";
  };
  "GET /me": {
    200: "me" | "me_auditor" | "me_dark" | "me_directory" | "me_english" | "me_estimator" | "me_grid_settings" | "me_manager" | "me_with_avatar" | "me_without_administration" | "me_without_preferences" | "me_without_roles";
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
    200: "project" | "project_completed" | "project_created" | "project_pricing" | "project_pricing_estimator" | "project_reader" | "project_revision_opened" | "project_without_current_revision";
  };
  "GET /projects/{project_id}/actual-costs": {
    200: "actual_costs" | "actual_costs_after_exclusion" | "actual_costs_empty" | "actual_costs_page" | "actual_costs_subproject";
  };
  "GET /projects/{project_id}/contributors": {
    200: "contributors" | "contributors_by_name" | "contributors_inactive" | "contributors_search";
  };
  "GET /projects/{project_id}/contributors/suggestions": {
    200: "contributor_suggestions" | "contributor_suggestions_empty";
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
    200: "import_actual_costs_analysed" | "import_analysed" | "import_analysing" | "import_planning_mismatch" | "import_planning_non_working_day" | "import_planning_rejected" | "import_remaining_analysed" | "import_remaining_subproject_held";
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
  "GET /projects/{project_id}/next-state": {
    200: "next_state" | "next_state_completed" | "next_state_created" | "next_state_pricing";
  };
  "GET /projects/{project_id}/remaining-indicators": {
    200: "remaining_indicators" | "remaining_indicators_over_budget";
  };
  "GET /projects/{project_id}/remaining-indicators/startable-tasks": {
    200: "startable_tasks" | "startable_tasks_milestone";
  };
  "GET /projects/{project_id}/revisions": {
    200: "revisions" | "revisions_designation_open" | "revisions_empty" | "revisions_marked";
  };
  "GET /projects/{project_id}/revisions/comparison": {
    200: "comparison" | "comparison_identical" | "comparison_moved" | "volume/comparison_volume";
  };
  "GET /projects/{project_id}/revisions/{revision_id}": {
    200: "revision" | "revision_estimator" | "revision_importing" | "revision_marked" | "revision_marking" | "revision_offer" | "revision_reader" | "revision_without_tasks";
  };
  "GET /projects/{project_id}/revisions/{revision_id}/rate-update": {
    200: "rate_update" | "rate_update_none";
  };
  "GET /projects/{project_id}/revisions/{revision_id}/structures": {
    200: "structures" | "structures_amendments" | "structures_estimator" | "structures_without_tasks";
  };
  "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/merge": {
    200: "structure_merge_report" | "structure_merge_report_refused" | "structure_merge_report_started_task";
  };
  "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes": {
    200: "nodes" | "nodes_amendment" | "nodes_core" | "nodes_empty" | "nodes_estimate" | "nodes_estimate_hours" | "nodes_estimate_sorted" | "nodes_installation" | "nodes_milestone" | "nodes_nested" | "nodes_planning" | "nodes_risk_occurred" | "nodes_summaries" | "nodes_summaries_leaves" | "nodes_timeline" | "volume/nodes_thousand";
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
    200: "subprojects" | "subprojects_by_label" | "subprojects_completed" | "subprojects_with_actual_costs";
  };
  "GET /projects/{project_id}/timelines": {
    200: "timelines" | "timelines_empty";
  };
  "GET /projects/{project_id}/work-breakdown": {
    200: "work_breakdown" | "work_breakdown_default" | "work_breakdown_order_items" | "work_breakdown_search";
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
    200: "cost_types" | "cost_types_reader" | "cost_types_with_inactive";
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
    200: "reference_readiness" | "reference_readiness_incomplete" | "reference_readiness_without_provision";
  };
  "GET /reference/resource-roles": {
    200: "resource_roles" | "resource_roles_bounded" | "resource_roles_reader";
  };
  "GET /reference/settings": {
    200: "reference_settings";
  };
  "GET /system/status": {
    200: "system_status" | "system_status_backup_failed" | "system_status_copy_failed" | "system_status_storage_full";
  };
  "GET /tasks": {
    200: "tasks_none" | "tasks_running";
  };
  "GET /tasks/{task_id}": {
    200: "identity_sync_succeeded" | "task_export_succeeded" | "task_failed" | "task_import_succeeded" | "task_interrupted_by_restore" | "task_mark_relaunched" | "task_merge_outside_work_package" | "task_merge_running" | "task_merge_succeeded" | "task_restore_backup_newer_version" | "task_restore_verification_failed" | "task_running" | "task_succeeded";
  };
  "GET /users": {
    200: "users" | "users_anonymized" | "users_by_access_role" | "users_by_created_at" | "users_created_by_platform" | "users_inactive" | "users_page" | "users_search";
  };
  "GET /users/{user_id}": {
    200: "user_anonymized" | "user_deactivated";
  };
  "PATCH /access-roles/{access_role_id}": {
    200: "access_role_marking_granted" | "access_role_renamed" | "access_role_updated";
  };
  "PATCH /backups/{backup_id}": {
    200: "backup_released" | "backup_retained";
  };
  "PATCH /me/preferences": {
    200: "preferences" | "preferences_dark" | "preferences_page_size" | "preferences_timeline_lanes";
  };
  "PATCH /projects/{project_id}": {
    200: "project_updated";
  };
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line": {
    200: "estimate_line_entered" | "estimate_line_redated" | "estimate_line_subproject_changed" | "estimate_line_updated" | "estimate_line_updated_amendment";
  };
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task": {
    200: "task_attached" | "task_dates_entered" | "task_description_entered" | "task_duration_entered" | "task_mode_changed" | "task_renamed" | "volume/task_lengthened";
  };
  "PATCH /projects/{project_id}/risks/{risk_id}": {
    200: "risk_updated";
  };
  "PATCH /projects/{project_id}/subprojects/{subproject_id}": {
    200: "subproject_updated";
  };
  "PATCH /reference/calendars/{calendar_id}": {
    200: "calendar_updated";
  };
  "PATCH /reference/cost-categories/{cost_category_id}": {
    200: "cost_category_updated";
  };
  "PATCH /reference/cost-types/{cost_type_id}": {
    200: "cost_type_updated";
  };
  "PATCH /reference/org-nodes/{org_node_id}": {
    200: "org_node_renamed_under_inactive" | "org_node_updated";
  };
  "PATCH /reference/resource-roles/{resource_role_id}": {
    200: "resource_role_updated";
  };
  "PATCH /reference/settings": {
    200: "reference_settings_matrix_updated" | "reference_settings_thresholds_updated";
  };
  "PATCH /users/{user_id}": {
    200: "user_renamed" | "user_renamed_deactivated";
  };
  "POST /access-roles": {
    201: "access_role_created";
  };
  "POST /backups": {
    202: "task_backup_queued";
  };
  "POST /chunked-uploads": {
    201: "chunked_upload";
  };
  "POST /chunked-uploads/{chunked_upload_id}/completion": {
    201: "chunked_upload_completed" | "file_upload_external_backup";
  };
  "POST /external-backup-locations/{location_name}/test": {
    200: "external_backup_location_test_failed" | "external_backup_location_tested";
  };
  "POST /file-uploads": {
    201: "file_upload";
  };
  "POST /identity-syncs": {
    202: "identity_sync_queued";
  };
  "POST /projects": {
    201: "project_created";
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
  "POST /projects/{project_id}/revisions": {
    201: "revision_created";
  };
  "POST /projects/{project_id}/revisions/{revision_id}/mark": {
    202: "task_mark_queued" | "task_mark_relaunched";
  };
  "POST /projects/{project_id}/revisions/{revision_id}/rate-update": {
    200: "rate_update_applied";
  };
  "POST /projects/{project_id}/revisions/{revision_id}/skeleton": {
    201: "skeleton_generated";
  };
  "POST /projects/{project_id}/revisions/{revision_id}/structures": {
    201: "amendment_created";
  };
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/merge": {
    202: "task_merge_queued";
  };
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes": {
    201: "estimate_line_created" | "estimate_line_created_after_subtask" | "node_created" | "node_created_child";
  };
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/move": {
    200: "nodes_indented" | "nodes_moved";
  };
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste": {
    200: "paste_applied" | "paste_applied_amendment" | "paste_applied_amendment_skipping" | "paste_applied_partial";
  };
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste-preview": {
    200: "paste_plan" | "paste_plan_amendment" | "paste_plan_amendment_skipping" | "paste_plan_subproject_held" | "paste_plan_unknown_category";
  };
  "POST /projects/{project_id}/risks": {
    201: "risk_created";
  };
  "POST /projects/{project_id}/risks/{risk_id}/occurrence": {
    202: "task_occurrence_queued";
  };
  "POST /projects/{project_id}/risks/{risk_id}/reviews": {
    201: "risk_reviewed";
  };
  "POST /projects/{project_id}/subprojects": {
    201: "subproject_created";
  };
  "POST /projects/{project_id}/timelines": {
    201: "timeline_created";
  };
  "POST /reference/calendars": {
    201: "calendar_created";
  };
  "POST /reference/cost-categories": {
    201: "cost_category_created";
  };
  "POST /reference/cost-types": {
    201: "cost_type_created";
  };
  "POST /reference/org-nodes": {
    201: "org_node_created";
  };
  "POST /reference/resource-roles": {
    201: "resource_role_created";
  };
  "POST /restores": {
    202: "task_restore_queued";
  };
  "POST /users": {
    201: "user_created" | "user_created_invited";
  };
  "POST /users/{user_id}/anonymization": {
    200: "user_anonymized";
  };
  "POST /users/{user_id}/password-link": {
    201: "password_setup_link";
  };
  "PUT /backup-schedule": {
    200: "backup_schedule_set";
  };
  "PUT /chunked-uploads/{chunked_upload_id}/parts/{part_number}": {
    200: "chunked_upload_part";
  };
  "PUT /projects/{project_id}/actual-costs/{cost_line_id}/tracked-scope": {
    200: "actual_cost_excluded" | "actual_cost_reinstated";
  };
  "PUT /projects/{project_id}/contributors": {
    200: "contributors_set";
  };
  "PUT /projects/{project_id}/reference-revision": {
    200: "reference_designated";
  };
  "PUT /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/predecessors": {
    200: "predecessor_set" | "predecessors_entered";
  };
  "PUT /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/progress": {
    200: "milestone_completed" | "milestone_reopened" | "task_reopened" | "task_started";
  };
  "PUT /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/remaining": {
    200: "remaining_reestimated";
  };
  "PUT /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/tracking": {
    200: "node_tracked";
  };
  "PUT /projects/{project_id}/work-breakdown": {
    200: "work_breakdown_saved";
  };
  "PUT /reference/calendars/{calendar_id}/activation": {
    200: "calendar_deactivated";
  };
  "PUT /reference/calendars/{calendar_id}/default": {
    200: "calendar_default";
  };
  "PUT /reference/cost-categories/{cost_category_id}/activation": {
    200: "cost_category_deactivated";
  };
  "PUT /reference/cost-categories/{cost_category_id}/hourly-rates/{year}": {
    200: "hourly_rate_added_year" | "hourly_rate_corrected" | "hourly_rate_entered";
  };
  "PUT /reference/cost-types/{cost_type_id}/activation": {
    200: "cost_type_deactivated";
  };
  "PUT /reference/duration-units": {
    200: "duration_units_updated";
  };
  "PUT /reference/org-nodes/{org_node_id}/activation": {
    200: "org_node_deactivated" | "org_node_reactivated";
  };
  "PUT /reference/resource-roles/{resource_role_id}/activation": {
    200: "resource_role_deactivated" | "resource_role_reactivated";
  };
  "PUT /users/{user_id}/access-roles": {
    200: "user_access_roles_cleared" | "user_access_roles_set" | "user_access_roles_two";
  };
  "PUT /users/{user_id}/activation": {
    200: "user_deactivated";
  };
}
