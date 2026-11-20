ALTER TABLE `task_events` ADD `definition_json` text;--> statement-breakpoint
ALTER TABLE `task_events` ADD `change_reason` text DEFAULT 'user_update' NOT NULL;--> statement-breakpoint
ALTER TABLE `task_state` ADD `definition_json` text;