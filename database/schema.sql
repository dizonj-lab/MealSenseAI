
\restrict y0Aepa2XP8nYzV1znJbKT4W7A7hZX8CAJl4HTNKghrjgn6g3bJrQSRNJaVw38GR

-- Dumped from database version 16.15

SET statement_timeout = 0;

SET default_tablespace = '';

SET default_table_access_method = heap;

--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);

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

CREATE SEQUENCE public.corrections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--

ALTER SEQUENCE public.corrections_id_seq OWNED BY public.corrections.id;

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

CREATE SEQUENCE public.experiments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--

ALTER SEQUENCE public.experiments_id_seq OWNED BY public.experiments.id;

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
    updated_at timestamp with time zone NOT NULL
);

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

CREATE SEQUENCE public.inference_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--

ALTER SEQUENCE public.inference_logs_id_seq OWNED BY public.inference_logs.id;

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

CREATE SEQUENCE public.meal_foods_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--

ALTER SEQUENCE public.meal_foods_id_seq OWNED BY public.meal_foods.id;

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

CREATE SEQUENCE public.meals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--

ALTER SEQUENCE public.meals_id_seq OWNED BY public.meals.id;

--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    name character varying(120) NOT NULL,
    password_hash character varying(255) NOT NULL,
    onboarded boolean NOT NULL,
    created_at timestamp with time zone NOT NULL
);

--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;

--

ALTER TABLE ONLY public.corrections ALTER COLUMN id SET DEFAULT nextval('public.corrections_id_seq'::regclass);

--

ALTER TABLE ONLY public.experiments ALTER COLUMN id SET DEFAULT nextval('public.experiments_id_seq'::regclass);

--

ALTER TABLE ONLY public.inference_logs ALTER COLUMN id SET DEFAULT nextval('public.inference_logs_id_seq'::regclass);

--

ALTER TABLE ONLY public.meal_foods ALTER COLUMN id SET DEFAULT nextval('public.meal_foods_id_seq'::regclass);

--

ALTER TABLE ONLY public.meals ALTER COLUMN id SET DEFAULT nextval('public.meals_id_seq'::regclass);

--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);

--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);

--

ALTER TABLE ONLY public.corrections
    ADD CONSTRAINT corrections_pkey PRIMARY KEY (id);

--

ALTER TABLE ONLY public.experiments
    ADD CONSTRAINT experiments_pkey PRIMARY KEY (id);

--

ALTER TABLE ONLY public.health_profiles
    ADD CONSTRAINT health_profiles_pkey PRIMARY KEY (user_id);

--

ALTER TABLE ONLY public.inference_logs
    ADD CONSTRAINT inference_logs_pkey PRIMARY KEY (id);

--

ALTER TABLE ONLY public.meal_foods
    ADD CONSTRAINT meal_foods_pkey PRIMARY KEY (id);

--

ALTER TABLE ONLY public.meals
    ADD CONSTRAINT meals_pkey PRIMARY KEY (id);

--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);

--

CREATE INDEX ix_corrections_meal_id ON public.corrections USING btree (meal_id);

--

CREATE INDEX ix_corrections_user_id ON public.corrections USING btree (user_id);

--

CREATE INDEX ix_inference_logs_meal_id ON public.inference_logs USING btree (meal_id);

--

CREATE INDEX ix_inference_logs_model_name ON public.inference_logs USING btree (model_name);

--

CREATE INDEX ix_meal_foods_meal_id ON public.meal_foods USING btree (meal_id);

--

CREATE INDEX ix_meals_eaten_at ON public.meals USING btree (eaten_at);

--

CREATE INDEX ix_meals_user_id ON public.meals USING btree (user_id);

--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);

--

ALTER TABLE ONLY public.corrections
    ADD CONSTRAINT corrections_meal_id_fkey FOREIGN KEY (meal_id) REFERENCES public.meals(id) ON DELETE CASCADE;

--

ALTER TABLE ONLY public.corrections
    ADD CONSTRAINT corrections_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

--

ALTER TABLE ONLY public.health_profiles
    ADD CONSTRAINT health_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

--

ALTER TABLE ONLY public.meal_foods
    ADD CONSTRAINT meal_foods_meal_id_fkey FOREIGN KEY (meal_id) REFERENCES public.meals(id) ON DELETE CASCADE;

--

ALTER TABLE ONLY public.meals
    ADD CONSTRAINT meals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

--

\unrestrict y0Aepa2XP8nYzV1znJbKT4W7A7hZX8CAJl4HTNKghrjgn6g3bJrQSRNJaVw38GR

