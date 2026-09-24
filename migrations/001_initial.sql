-- Reference initial PostgreSQL schema. Startup creates an equivalent fresh schema.

CREATE TABLE accounts (
	id VARCHAR NOT NULL, 
	data JSON, 
	PRIMARY KEY (id)
)

;


CREATE TABLE documents (
	id VARCHAR NOT NULL, 
	metadata_json JSON, 
	body TEXT, 
	PRIMARY KEY (id)
)

;


CREATE TABLE feedback (
	id VARCHAR NOT NULL, 
	user_id VARCHAR, 
	response_id VARCHAR, 
	helpful BOOLEAN, 
	PRIMARY KEY (id)
)

;


CREATE TABLE messages (
	id VARCHAR NOT NULL, 
	thread_id VARCHAR, 
	user_id VARCHAR, 
	role VARCHAR, 
	content TEXT, 
	payload JSON, 
	created_at VARCHAR, 
	PRIMARY KEY (id)
)

;


CREATE TABLE orders (
	id VARCHAR NOT NULL, 
	account_id VARCHAR, 
	data JSON, 
	PRIMARY KEY (id)
)

;


CREATE TABLE requests (
	id VARCHAR NOT NULL, 
	user_id VARCHAR, 
	trace_id VARCHAR, 
	latency FLOAT, 
	escalation BOOLEAN, 
	error BOOLEAN, 
	route VARCHAR, 
	created_at VARCHAR, 
	PRIMARY KEY (id)
)

;


CREATE TABLE threads (
	id VARCHAR NOT NULL, 
	user_id VARCHAR, 
	title VARCHAR, 
	PRIMARY KEY (id)
)

;


CREATE TABLE tickets (
	id VARCHAR NOT NULL, 
	user_id VARCHAR, 
	account_id VARCHAR, 
	thread_id VARCHAR, 
	request_id VARCHAR, 
	data JSON, 
	PRIMARY KEY (id), 
	UNIQUE (request_id)
)

;


CREATE TABLE users (
	id VARCHAR NOT NULL, 
	account_id VARCHAR NOT NULL, 
	verified BOOLEAN, 
	role VARCHAR, 
	PRIMARY KEY (id)
)

;

CREATE INDEX ix_messages_thread_id ON messages (thread_id);

CREATE INDEX ix_messages_user_id ON messages (user_id);

CREATE INDEX ix_orders_account_id ON orders (account_id);

CREATE INDEX ix_requests_user_id ON requests (user_id);

CREATE INDEX ix_threads_user_id ON threads (user_id);

CREATE INDEX ix_tickets_user_id ON tickets (user_id);