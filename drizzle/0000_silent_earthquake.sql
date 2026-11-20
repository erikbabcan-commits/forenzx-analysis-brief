CREATE TABLE `task_events` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`task_id` text NOT NULL,
	`from_status` text NOT NULL,
	`to_status` text NOT NULL,
	`evidence` text NOT NULL,
	`checks_json` text NOT NULL,
	`revision` integer NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `task_events_user_time` ON `task_events` (`user_id`,`created_at`);--> statement-breakpoint
CREATE UNIQUE INDEX `task_events_user_task_revision` ON `task_events` (`user_id`,`task_id`,`revision`);--> statement-breakpoint
CREATE TABLE `task_state` (
	`user_id` text NOT NULL,
	`task_id` text NOT NULL,
	`status` text NOT NULL,
	`evidence` text DEFAULT '' NOT NULL,
	`checks_json` text DEFAULT '[]' NOT NULL,
	`revision` integer DEFAULT 0 NOT NULL,
	`updated_at` text,
	`last_mutation_id` text,
	PRIMARY KEY(`user_id`, `task_id`)
);
