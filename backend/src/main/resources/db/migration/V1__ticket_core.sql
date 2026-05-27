create table support_tickets (
    id binary(16) not null primary key,
    tenant_id varchar(64) not null,
    title varchar(180) not null,
    customer_name varchar(120) not null,
    customer_message text not null,
    status varchar(32) not null,
    priority varchar(32) not null,
    assigned_agent_id varchar(64),
    handoff_reason varchar(255),
    sla_due_at timestamp null,
    claimed_at timestamp null,
    created_at timestamp not null,
    updated_at timestamp not null,
    version bigint not null,
    index idx_ticket_queue (tenant_id, status, priority, created_at),
    index idx_ticket_assignee (tenant_id, assigned_agent_id, status)
);

create table ticket_events (
    id binary(16) not null primary key,
    ticket_id binary(16) not null,
    tenant_id varchar(64) not null,
    event_type varchar(64) not null,
    actor_id varchar(64) not null,
    from_status varchar(32),
    to_status varchar(32),
    reason varchar(255),
    created_at timestamp not null,
    index idx_ticket_events_ticket (ticket_id, created_at)
);

create table ticket_ai_assists (
    id binary(16) not null primary key,
    ticket_id binary(16) not null,
    source_event_id varchar(80) not null,
    intent varchar(80) not null,
    summary varchar(500) not null,
    suggested_reply text not null,
    handoff_recommended boolean not null,
    handoff_reason varchar(255),
    sla_risk varchar(32) not null,
    confidence decimal(5, 4) not null,
    citations_json text,
    latency_ms integer not null,
    estimated_cost_usd decimal(10, 6) not null,
    created_at timestamp not null,
    unique key uk_ai_assist_event (ticket_id, source_event_id),
    index idx_ai_assists_ticket (ticket_id, created_at)
);
