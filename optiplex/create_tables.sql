create table groupIDs
(
	id int not null
		constraint groupIDs_pk
			primary key,
	name TEST not null
);

create index groupIDs__name
	on groupIDs (name);

create unique index groupIDs_id_uindex
	on groupIDs (id);

create table icons
(
	iconID int not null
		constraint icons_pk
			primary key,
	filename TEXT
);

create table typeIDs
(
	id int not null
		constraint typeIDs_pk
			primary key,
	name TEXT,
	group_id int not null
		references groupIDs,
	iconID int
);

create unique index blueprints_id_uindex
	on typeIDs (id);

create index typeIDs__name
	on typeIDs (name);




create table blueprints
(
	id int not null
		constraint blueprints_pk
			primary key,
	product_typeID int not null
		references typeIDs,
	product_quantity int not null
);

create table blueprint_materials
(
	blueprint_id int not null,
	material_id int not null,
	material_quantity int not null
);

create table prices
(
	typeID int not null
		constraint prices_pk
			primary key
		references typeIDs,
	buy float not null,
	sell float not null
);

create unique index prices_typeID_uindex
	on prices (typeID);




