--
-- PostgreSQL database dump
--

\restrict PhIOHdSFhHbQOLWQQwCKKUL2RAeX0UuMbMEglfNKYAvNBX3Duq0fNybPNDAoeEZ

-- Dumped from database version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: app_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.app_settings (
    key character varying(80) NOT NULL,
    value json,
    updated_by integer,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_log (
    id integer NOT NULL,
    actor_id integer,
    action character varying(60) NOT NULL,
    target_type character varying(40),
    target_id character varying(80),
    detail json NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_log_id_seq OWNED BY public.audit_log.id;


--
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_messages (
    id integer NOT NULL,
    thread_id integer NOT NULL,
    role character varying(10) NOT NULL,
    content text NOT NULL,
    meta json NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: chat_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chat_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chat_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chat_messages_id_seq OWNED BY public.chat_messages.id;


--
-- Name: chat_threads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_threads (
    id integer NOT NULL,
    user_id integer NOT NULL,
    meal_id integer,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: chat_threads_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chat_threads_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chat_threads_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chat_threads_id_seq OWNED BY public.chat_threads.id;


--
-- Name: contact_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contact_messages (
    id integer NOT NULL,
    name character varying(120) NOT NULL,
    email character varying(255) NOT NULL,
    topic character varying(40) NOT NULL,
    message text NOT NULL,
    email_status character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: contact_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contact_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contact_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contact_messages_id_seq OWNED BY public.contact_messages.id;


--
-- Name: corrections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.corrections (
    id integer NOT NULL,
    user_id integer NOT NULL,
    meal_id integer NOT NULL,
    food_id integer,
    kind character varying(20) NOT NULL,
    before json,
    after json,
    model_name character varying(80),
    created_at timestamp with time zone NOT NULL
);


--
-- Name: corrections_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.corrections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: corrections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.corrections_id_seq OWNED BY public.corrections.id;


--
-- Name: custom_foods; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.custom_foods (
    id integer NOT NULL,
    user_id integer NOT NULL,
    name character varying(120) NOT NULL,
    serving_g double precision NOT NULL,
    serving_desc character varying(80) NOT NULL,
    per_100g json NOT NULL,
    glycemic_index double precision,
    aliases json NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: custom_foods_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.custom_foods_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: custom_foods_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.custom_foods_id_seq OWNED BY public.custom_foods.id;


--
-- Name: dataset_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dataset_versions (
    id integer NOT NULL,
    name character varying(60) NOT NULL,
    status character varying(20) NOT NULL,
    parent_id integer,
    created_by integer,
    notes character varying(500),
    manifest json NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: dataset_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.dataset_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dataset_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.dataset_versions_id_seq OWNED BY public.dataset_versions.id;


--
-- Name: experiments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.experiments (
    id integer NOT NULL,
    name character varying(120) NOT NULL,
    model_name character varying(80) NOT NULL,
    dataset character varying(200) NOT NULL,
    n_samples integer NOT NULL,
    has_ground_truth boolean NOT NULL,
    metrics json NOT NULL,
    notes text,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: experiments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.experiments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: experiments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.experiments_id_seq OWNED BY public.experiments.id;


--
-- Name: glucose_readings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.glucose_readings (
    id integer NOT NULL,
    user_id integer NOT NULL,
    meal_id integer,
    measured_at timestamp with time zone NOT NULL,
    value_mmol double precision NOT NULL,
    entered_unit character varying(10) NOT NULL,
    context character varying(20) NOT NULL,
    source character varying(20) NOT NULL,
    note character varying(200),
    created_at timestamp with time zone NOT NULL
);


--
-- Name: glucose_readings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.glucose_readings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: glucose_readings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.glucose_readings_id_seq OWNED BY public.glucose_readings.id;


--
-- Name: health_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.health_profiles (
    user_id integer NOT NULL,
    health_consent boolean NOT NULL,
    age integer,
    sex character varying(20),
    height_cm double precision,
    weight_kg double precision,
    activity_level character varying(20),
    diet_preferences json NOT NULL,
    diabetes_status character varying(30),
    allergies json NOT NULL,
    restrictions json NOT NULL,
    glucose_unit character varying(10) NOT NULL,
    known_readings text,
    hba1c double precision,
    has_cgm boolean,
    clinician_targets text,
    goals json NOT NULL,
    calorie_goal double precision,
    carb_goal_g double precision,
    protein_goal_g double precision,
    updated_at timestamp with time zone NOT NULL,
    age_range character varying(10),
    other_goal character varying(200)
);


--
-- Name: inference_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inference_logs (
    id integer NOT NULL,
    meal_id integer,
    model_name character varying(80) NOT NULL,
    model_version character varying(80) NOT NULL,
    task character varying(40) NOT NULL,
    ok boolean NOT NULL,
    latency_ms double precision NOT NULL,
    tokens integer,
    extra json NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: inference_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inference_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inference_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.inference_logs_id_seq OWNED BY public.inference_logs.id;


--
-- Name: meal_foods; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.meal_foods (
    id integer NOT NULL,
    meal_id integer NOT NULL,
    origin character varying(20) NOT NULL,
    label character varying(200) NOT NULL,
    nutrition_key character varying(80),
    mapping_quality character varying(20) NOT NULL,
    original_prediction json,
    grams double precision NOT NULL,
    portion json NOT NULL,
    nutrients json NOT NULL,
    nutrition_source json,
    confirmed boolean NOT NULL,
    user_corrected boolean NOT NULL,
    removed boolean NOT NULL,
    taxonomy_class character varying(120)
);


--
-- Name: meal_foods_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.meal_foods_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: meal_foods_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.meal_foods_id_seq OWNED BY public.meal_foods.id;


--
-- Name: meals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.meals (
    id integer NOT NULL,
    user_id integer NOT NULL,
    status character varying(20) NOT NULL,
    meal_type character varying(20),
    description text,
    reference_object character varying(40),
    serving_note text,
    images json NOT NULL,
    totals json NOT NULL,
    insights json NOT NULL,
    model_info json NOT NULL,
    stages json NOT NULL,
    eaten_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: meals_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.meals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: meals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.meals_id_seq OWNED BY public.meals.id;


--
-- Name: model_candidates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_candidates (
    id integer NOT NULL,
    name character varying(60) NOT NULL,
    dataset_version_id integer,
    report json NOT NULL,
    gate json NOT NULL,
    status character varying(20) NOT NULL,
    shadow json NOT NULL,
    created_by integer,
    decided_by integer,
    decided_at timestamp with time zone,
    note character varying(500),
    created_at timestamp with time zone NOT NULL
);


--
-- Name: model_candidates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.model_candidates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: model_candidates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.model_candidates_id_seq OWNED BY public.model_candidates.id;


--
-- Name: prompt_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prompt_versions (
    id integer NOT NULL,
    key character varying(60) NOT NULL,
    version integer NOT NULL,
    text text NOT NULL,
    note character varying(300),
    active boolean DEFAULT false NOT NULL,
    created_by integer,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: prompt_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.prompt_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: prompt_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.prompt_versions_id_seq OWNED BY public.prompt_versions.id;


--
-- Name: training_samples; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.training_samples (
    id integer NOT NULL,
    user_id integer NOT NULL,
    meal_id integer,
    food_id integer,
    view character varying(10) NOT NULL,
    image_path character varying(500) NOT NULL,
    bbox json,
    label character varying(120) NOT NULL,
    nutrition_key character varying(80),
    taxonomy_class character varying(120),
    custom_food_id integer,
    model_label character varying(120),
    model_score double precision,
    fingerprint json NOT NULL,
    source character varying(20) NOT NULL,
    model_version character varying(80),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    consent_at timestamp with time zone,
    withdrawn_at timestamp with time zone,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    reasons json DEFAULT '[]'::json NOT NULL,
    audit boolean DEFAULT false NOT NULL,
    model_candidates json DEFAULT '[]'::json NOT NULL,
    image_sha256 character varying(64),
    phash character varying(16),
    screened_at timestamp with time zone,
    reviewed_by integer,
    reviewed_at timestamp with time zone,
    review_note character varying(300)
);


--
-- Name: training_samples_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.training_samples_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: training_samples_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.training_samples_id_seq OWNED BY public.training_samples.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    name character varying(120) NOT NULL,
    password_hash character varying(255) NOT NULL,
    onboarded boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    training_consent boolean DEFAULT false NOT NULL,
    is_admin boolean DEFAULT false NOT NULL,
    email_verified_at timestamp with time zone,
    contributor_status character varying(20) DEFAULT 'active'::character varying NOT NULL
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: audit_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.audit_log_id_seq'::regclass);


--
-- Name: chat_messages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages ALTER COLUMN id SET DEFAULT nextval('public.chat_messages_id_seq'::regclass);


--
-- Name: chat_threads id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_threads ALTER COLUMN id SET DEFAULT nextval('public.chat_threads_id_seq'::regclass);


--
-- Name: contact_messages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_messages ALTER COLUMN id SET DEFAULT nextval('public.contact_messages_id_seq'::regclass);


--
-- Name: corrections id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.corrections ALTER COLUMN id SET DEFAULT nextval('public.corrections_id_seq'::regclass);


--
-- Name: custom_foods id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.custom_foods ALTER COLUMN id SET DEFAULT nextval('public.custom_foods_id_seq'::regclass);


--
-- Name: dataset_versions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_versions ALTER COLUMN id SET DEFAULT nextval('public.dataset_versions_id_seq'::regclass);


--
-- Name: experiments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.experiments ALTER COLUMN id SET DEFAULT nextval('public.experiments_id_seq'::regclass);


--
-- Name: glucose_readings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.glucose_readings ALTER COLUMN id SET DEFAULT nextval('public.glucose_readings_id_seq'::regclass);


--
-- Name: inference_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inference_logs ALTER COLUMN id SET DEFAULT nextval('public.inference_logs_id_seq'::regclass);


--
-- Name: meal_foods id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.meal_foods ALTER COLUMN id SET DEFAULT nextval('public.meal_foods_id_seq'::regclass);


--
-- Name: meals id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.meals ALTER COLUMN id SET DEFAULT nextval('public.meals_id_seq'::regclass);


--
-- Name: model_candidates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_candidates ALTER COLUMN id SET DEFAULT nextval('public.model_candidates_id_seq'::regclass);


--
-- Name: prompt_versions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prompt_versions ALTER COLUMN id SET DEFAULT nextval('public.prompt_versions_id_seq'::regclass);


--
-- Name: training_samples id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_samples ALTER COLUMN id SET DEFAULT nextval('public.training_samples_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: app_settings app_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_settings
    ADD CONSTRAINT app_settings_pkey PRIMARY KEY (key);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id);


--
-- Name: chat_threads chat_threads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_threads
    ADD CONSTRAINT chat_threads_pkey PRIMARY KEY (id);


--
-- Name: contact_messages contact_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_messages
    ADD CONSTRAINT contact_messages_pkey PRIMARY KEY (id);


--
-- Name: corrections corrections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.corrections
    ADD CONSTRAINT corrections_pkey PRIMARY KEY (id);


--
-- Name: custom_foods custom_foods_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.custom_foods
    ADD CONSTRAINT custom_foods_pkey PRIMARY KEY (id);


--
-- Name: dataset_versions dataset_versions_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_versions
    ADD CONSTRAINT dataset_versions_name_key UNIQUE (name);


--
-- Name: dataset_versions dataset_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_versions
    ADD CONSTRAINT dataset_versions_pkey PRIMARY KEY (id);


--
-- Name: experiments experiments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.experiments
    ADD CONSTRAINT experiments_pkey PRIMARY KEY (id);


--
-- Name: glucose_readings glucose_readings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.glucose_readings
    ADD CONSTRAINT glucose_readings_pkey PRIMARY KEY (id);


--
-- Name: health_profiles health_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.health_profiles
    ADD CONSTRAINT health_profiles_pkey PRIMARY KEY (user_id);


--
-- Name: inference_logs inference_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inference_logs
    ADD CONSTRAINT inference_logs_pkey PRIMARY KEY (id);


--
-- Name: meal_foods meal_foods_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.meal_foods
    ADD CONSTRAINT meal_foods_pkey PRIMARY KEY (id);


--
-- Name: meals meals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.meals
    ADD CONSTRAINT meals_pkey PRIMARY KEY (id);


--
-- Name: model_candidates model_candidates_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_candidates
    ADD CONSTRAINT model_candidates_name_key UNIQUE (name);


--
-- Name: model_candidates model_candidates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_candidates
    ADD CONSTRAINT model_candidates_pkey PRIMARY KEY (id);


--
-- Name: prompt_versions prompt_versions_key_version_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prompt_versions
    ADD CONSTRAINT prompt_versions_key_version_key UNIQUE (key, version);


--
-- Name: prompt_versions prompt_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prompt_versions
    ADD CONSTRAINT prompt_versions_pkey PRIMARY KEY (id);


--
-- Name: training_samples training_samples_food_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_samples
    ADD CONSTRAINT training_samples_food_id_key UNIQUE (food_id);


--
-- Name: training_samples training_samples_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_samples
    ADD CONSTRAINT training_samples_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_audit_log_actor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_actor_id ON public.audit_log USING btree (actor_id);


--
-- Name: ix_audit_log_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_created_at ON public.audit_log USING btree (created_at);


--
-- Name: ix_chat_messages_thread_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_messages_thread_id ON public.chat_messages USING btree (thread_id);


--
-- Name: ix_chat_threads_meal_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_threads_meal_id ON public.chat_threads USING btree (meal_id);


--
-- Name: ix_chat_threads_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_threads_updated_at ON public.chat_threads USING btree (updated_at);


--
-- Name: ix_chat_threads_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_threads_user_id ON public.chat_threads USING btree (user_id);


--
-- Name: ix_contact_messages_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contact_messages_created_at ON public.contact_messages USING btree (created_at);


--
-- Name: ix_corrections_meal_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_corrections_meal_id ON public.corrections USING btree (meal_id);


--
-- Name: ix_corrections_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_corrections_user_id ON public.corrections USING btree (user_id);


--
-- Name: ix_custom_foods_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_custom_foods_user_id ON public.custom_foods USING btree (user_id);


--
-- Name: ix_glucose_readings_meal_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_glucose_readings_meal_id ON public.glucose_readings USING btree (meal_id);


--
-- Name: ix_glucose_readings_measured_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_glucose_readings_measured_at ON public.glucose_readings USING btree (measured_at);


--
-- Name: ix_glucose_readings_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_glucose_readings_user_id ON public.glucose_readings USING btree (user_id);


--
-- Name: ix_inference_logs_meal_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inference_logs_meal_id ON public.inference_logs USING btree (meal_id);


--
-- Name: ix_inference_logs_model_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inference_logs_model_name ON public.inference_logs USING btree (model_name);


--
-- Name: ix_meal_foods_meal_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_meal_foods_meal_id ON public.meal_foods USING btree (meal_id);


--
-- Name: ix_meals_eaten_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_meals_eaten_at ON public.meals USING btree (eaten_at);


--
-- Name: ix_meals_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_meals_user_id ON public.meals USING btree (user_id);


--
-- Name: ix_prompt_versions_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_prompt_versions_key ON public.prompt_versions USING btree (key);


--
-- Name: ix_training_samples_image_sha256; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_training_samples_image_sha256 ON public.training_samples USING btree (image_sha256);


--
-- Name: ix_training_samples_label; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_training_samples_label ON public.training_samples USING btree (label);


--
-- Name: ix_training_samples_meal_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_training_samples_meal_id ON public.training_samples USING btree (meal_id);


--
-- Name: ix_training_samples_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_training_samples_status ON public.training_samples USING btree (status);


--
-- Name: ix_training_samples_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_training_samples_user_id ON public.training_samples USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: app_settings app_settings_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_settings
    ADD CONSTRAINT app_settings_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: audit_log audit_log_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: chat_messages chat_messages_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.chat_threads(id) ON DELETE CASCADE;


--
-- Name: chat_threads chat_threads_meal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_threads
    ADD CONSTRAINT chat_threads_meal_id_fkey FOREIGN KEY (meal_id) REFERENCES public.meals(id) ON DELETE CASCADE;


--
-- Name: chat_threads chat_threads_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_threads
    ADD CONSTRAINT chat_threads_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: corrections corrections_meal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.corrections
    ADD CONSTRAINT corrections_meal_id_fkey FOREIGN KEY (meal_id) REFERENCES public.meals(id) ON DELETE CASCADE;


--
-- Name: corrections corrections_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.corrections
    ADD CONSTRAINT corrections_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: custom_foods custom_foods_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.custom_foods
    ADD CONSTRAINT custom_foods_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: dataset_versions dataset_versions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_versions
    ADD CONSTRAINT dataset_versions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: dataset_versions dataset_versions_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_versions
    ADD CONSTRAINT dataset_versions_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.dataset_versions(id) ON DELETE SET NULL;


--
-- Name: glucose_readings glucose_readings_meal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.glucose_readings
    ADD CONSTRAINT glucose_readings_meal_id_fkey FOREIGN KEY (meal_id) REFERENCES public.meals(id) ON DELETE SET NULL;


--
-- Name: glucose_readings glucose_readings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.glucose_readings
    ADD CONSTRAINT glucose_readings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: health_profiles health_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.health_profiles
    ADD CONSTRAINT health_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: meal_foods meal_foods_meal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.meal_foods
    ADD CONSTRAINT meal_foods_meal_id_fkey FOREIGN KEY (meal_id) REFERENCES public.meals(id) ON DELETE CASCADE;


--
-- Name: meals meals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.meals
    ADD CONSTRAINT meals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: model_candidates model_candidates_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_candidates
    ADD CONSTRAINT model_candidates_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: model_candidates model_candidates_dataset_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_candidates
    ADD CONSTRAINT model_candidates_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES public.dataset_versions(id) ON DELETE SET NULL;


--
-- Name: model_candidates model_candidates_decided_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_candidates
    ADD CONSTRAINT model_candidates_decided_by_fkey FOREIGN KEY (decided_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: prompt_versions prompt_versions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prompt_versions
    ADD CONSTRAINT prompt_versions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: training_samples training_samples_custom_food_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_samples
    ADD CONSTRAINT training_samples_custom_food_id_fkey FOREIGN KEY (custom_food_id) REFERENCES public.custom_foods(id) ON DELETE SET NULL;


--
-- Name: training_samples training_samples_meal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_samples
    ADD CONSTRAINT training_samples_meal_id_fkey FOREIGN KEY (meal_id) REFERENCES public.meals(id) ON DELETE CASCADE;


--
-- Name: training_samples training_samples_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_samples
    ADD CONSTRAINT training_samples_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: training_samples training_samples_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_samples
    ADD CONSTRAINT training_samples_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict PhIOHdSFhHbQOLWQQwCKKUL2RAeX0UuMbMEglfNKYAvNBX3Duq0fNybPNDAoeEZ

