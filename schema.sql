-- ================================================================
-- STEP 1 - CREATE TABLES (no FK constraints yet)
-- ================================================================

CREATE TABLE material_master (
    Material_Number         VARCHAR(20)     NOT NULL,
    Material_Type           VARCHAR(30)     NOT NULL,
    Description             VARCHAR(120)    NOT NULL,
    Base_Unit               VARCHAR(5)      NOT NULL,
    Material_Group          VARCHAR(20)     NOT NULL,
    Net_Weight_KG           NUMERIC(10,3)   NOT NULL,
    Gross_Weight_KG         NUMERIC(10,3)   NOT NULL,
    Standard_Price_USD      NUMERIC(12,4)   NOT NULL,
    Valuation_Class         VARCHAR(10)     NOT NULL,
    Plant                   VARCHAR(10)     NOT NULL,
    Storage_Location        VARCHAR(10)     NOT NULL,
    ABC_Indicator           CHAR(1)         NOT NULL,
    MRP_Type                VARCHAR(5)      NOT NULL,
    Safety_Stock            INTEGER         NOT NULL DEFAULT 0,
    Lot_Size                INTEGER         NOT NULL DEFAULT 10,
    Procurement_Type        CHAR(1)         NOT NULL,
    Created_Date            DATE            NOT NULL DEFAULT CURRENT_DATE,
    Quality_Inspection      CHAR(1)         NOT NULL,
    Lead_Time_Days          INTEGER         NOT NULL DEFAULT 14,
    PRIMARY KEY (Material_Number)
);

-- NOTE: No serial id column. Composite PK matches CSV structure.
CREATE TABLE bill_of_materials (
    BOM_Number              VARCHAR(10)     NOT NULL,
    Parent_Material         VARCHAR(20)     NOT NULL,
    Parent_Description      VARCHAR(120),
    Component_Material      VARCHAR(20)     NOT NULL,
    Component_Description   VARCHAR(120),
    Component_Type          VARCHAR(30)     NOT NULL,
    Component_Quantity      NUMERIC(12,4)   NOT NULL,
    Component_Unit          VARCHAR(5)      NOT NULL,
    Item_Number             INTEGER         NOT NULL,
    BOM_Level               SMALLINT        NOT NULL DEFAULT 1,
    Valid_From              DATE            NOT NULL,
    Valid_To                DATE            NOT NULL,
    BOM_Status              VARCHAR(10)     NOT NULL DEFAULT 'ACTIVE',
    Scrap_Percentage        NUMERIC(5,2)    NOT NULL DEFAULT 0,
    Plant                   VARCHAR(10)     NOT NULL,
    Component_Criticality   VARCHAR(10)     NOT NULL,
    PRIMARY KEY (BOM_Number, Component_Material)
);

CREATE TABLE production_orders (
    Production_Order        VARCHAR(10)     NOT NULL,
    Order_Type              VARCHAR(6)      NOT NULL DEFAULT 'YP01',
    Material_Number         VARCHAR(20)     NOT NULL,
    Product_Type            VARCHAR(20)     NOT NULL,
    Alloy_Grade             VARCHAR(6)      NOT NULL,
    Plant                   VARCHAR(10)     NOT NULL,
    Order_Quantity          INTEGER         NOT NULL,
    Confirmed_Quantity      INTEGER         NOT NULL DEFAULT 0,
    Scrap_Quantity          INTEGER         NOT NULL DEFAULT 0,
    Unit                    VARCHAR(5)      NOT NULL DEFAULT 'EA',
    Planned_Start_Date      DATE            NOT NULL,
    Planned_End_Date        DATE            NOT NULL,
    Actual_Start_Date       DATE,
    Actual_End_Date         DATE,
    Order_Status            VARCHAR(15)     NOT NULL DEFAULT 'CREATED',
    Priority                SMALLINT        NOT NULL DEFAULT 3,
    Production_Supervisor   VARCHAR(10),
    BOM_Number              VARCHAR(10),
    Sales_Order             VARCHAR(15),
    Customer                VARCHAR(15),
    Planned_Costs_USD       NUMERIC(14,2)   NOT NULL DEFAULT 0,
    Actual_Costs_USD        NUMERIC(14,2)   NOT NULL DEFAULT 0,
    Standard_Cost_USD       NUMERIC(14,2)   NOT NULL DEFAULT 0,
    Cost_Variance_USD       NUMERIC(14,2)   NOT NULL DEFAULT 0,
    Created_By              VARCHAR(10)     NOT NULL,
    Created_Date            DATE            NOT NULL DEFAULT CURRENT_DATE,
    PRIMARY KEY (Production_Order)
);

CREATE TABLE melting_heat_records (
    Heat_Number             VARCHAR(10)     NOT NULL,
    Furnace_ID              VARCHAR(12)     NOT NULL,
    Furnace_Type            VARCHAR(15)     NOT NULL,
    Plant                   VARCHAR(10)     NOT NULL,
    Melt_Date               DATE            NOT NULL,
    Shift                   CHAR(1)         NOT NULL,
    Operator_ID             VARCHAR(10)     NOT NULL,
    Target_Alloy            VARCHAR(6)      NOT NULL,
    Charge_Weight_KG        INTEGER         NOT NULL,
    Pig_Iron_KG             INTEGER         NOT NULL,
    Scrap_Steel_KG          INTEGER         NOT NULL,
    Returns_KG              INTEGER         NOT NULL,
    Alloy_Additions_KG      NUMERIC(8,1)    NOT NULL,
    Carbon_Pct              NUMERIC(5,3)    NOT NULL,
    Silicon_Pct             NUMERIC(5,3)    NOT NULL,
    Manganese_Pct           NUMERIC(5,3)    NOT NULL,
    Phosphorus_Pct          NUMERIC(6,4)    NOT NULL,
    Sulfur_Pct              NUMERIC(6,4)    NOT NULL,
    Chromium_Pct            NUMERIC(5,3)    NOT NULL DEFAULT 0,
    Nickel_Pct              NUMERIC(5,3)    NOT NULL DEFAULT 0,
    Molybdenum_Pct          NUMERIC(5,3)    NOT NULL DEFAULT 0,
    Copper_Pct              NUMERIC(5,3)    NOT NULL DEFAULT 0,
    Tap_Temperature_C       NUMERIC(7,1)    NOT NULL,
    Pour_Temperature_C      NUMERIC(7,1)    NOT NULL,
    Holding_Time_Min        INTEGER         NOT NULL,
    Inoculation_Type        VARCHAR(20)     NOT NULL,
    Inoculation_KG          NUMERIC(6,2)    NOT NULL DEFAULT 0,
    Spectro_Test_ID         VARCHAR(15)     NOT NULL,
    Quality_Status          VARCHAR(10)     NOT NULL,
    Rejection_Reason        VARCHAR(40),
    Yield_Pct               NUMERIC(5,2)    NOT NULL,
    Energy_KWH              NUMERIC(10,1)   NOT NULL,
    Melting_Duration_Min    INTEGER         NOT NULL,
    PRIMARY KEY (Heat_Number)
);

CREATE TABLE molding_records (
    Mold_Batch              VARCHAR(12)     NOT NULL,
    Production_Order        VARCHAR(10)     NOT NULL,
    Molding_Line            VARCHAR(6)      NOT NULL,
    Molding_Type            VARCHAR(15)     NOT NULL,
    Product_Type            VARCHAR(20)     NOT NULL,
    Alloy_Grade             VARCHAR(6)      NOT NULL,
    Mold_Date               DATE            NOT NULL,
    Shift                   CHAR(1)         NOT NULL,
    Operator_ID             VARCHAR(10)     NOT NULL,
    Planned_Quantity        INTEGER         NOT NULL,
    Actual_Quantity         INTEGER         NOT NULL,
    Sand_Type               VARCHAR(10)     NOT NULL,
    Binder_Type             VARCHAR(20)     NOT NULL,
    Binder_Percentage       NUMERIC(4,2)    NOT NULL,
    Moisture_Content_Pct    NUMERIC(4,2),
    Compressive_Strength_KPA NUMERIC(6,1),
    Permeability            NUMERIC(6,0),
    Mold_Hardness           SMALLINT,
    Core_Count              SMALLINT,
    Cycle_Time_Seconds      INTEGER,
    Sand_Temperature_C      NUMERIC(4,1),
    Ambient_Humidity_Pct    NUMERIC(5,2),
    Quality_Check           VARCHAR(6)      NOT NULL,
    Defect_Type             VARCHAR(20),
    Mold_Weight_KG          NUMERIC(8,1),
    Setup_Time_Min          INTEGER,
    Pattern_Number          VARCHAR(12),
    Sand_Mix_Batch          VARCHAR(12),
    PRIMARY KEY (Mold_Batch)
);

CREATE TABLE casting_records (
    Casting_Batch           VARCHAR(10)     NOT NULL,
    Heat_Number             VARCHAR(10)     NOT NULL,
    Production_Order        VARCHAR(10)     NOT NULL,
    Mold_Batch              VARCHAR(12),
    Casting_Date            DATE            NOT NULL,
    Shift                   CHAR(1)         NOT NULL,
    Operator_ID             VARCHAR(10)     NOT NULL,
    Product_Type            VARCHAR(20)     NOT NULL,
    Alloy_Grade             VARCHAR(6)      NOT NULL,
    Ladle_Number            VARCHAR(8)      NOT NULL,
    Ladle_Capacity_KG       INTEGER         NOT NULL,
    Metal_Weight_Poured_KG  NUMERIC(10,1)   NOT NULL,
    Pouring_Temperature_C   NUMERIC(7,1)    NOT NULL,
    Pouring_Rate_KG_MIN     NUMERIC(7,1)    NOT NULL,
    Molds_Poured            INTEGER         NOT NULL,
    Expected_Castings       INTEGER         NOT NULL,
    Good_Castings           INTEGER         NOT NULL,
    Scrap_Castings          INTEGER         NOT NULL,
    Yield_Pct               NUMERIC(5,2)    NOT NULL,
    Gating_System           VARCHAR(10)     NOT NULL,
    Riser_Type              VARCHAR(12)     NOT NULL,
    Cooling_Time_Hours      NUMERIC(5,1)    NOT NULL,
    Ambient_Temperature_C   NUMERIC(5,1),
    Pouring_Height_MM       INTEGER,
    Filter_Used             VARCHAR(3)      NOT NULL,
    Filter_Type             VARCHAR(20),
    Inoculation_In_Ladle    VARCHAR(3)      NOT NULL,
    Defects_Detected        VARCHAR(20),
    Quality_Grade           CHAR(1)         NOT NULL,
    PRIMARY KEY (Casting_Batch)
);

CREATE TABLE heat_treatment (
    HT_Batch_Number         VARCHAR(10)     NOT NULL,
    Casting_Batch           VARCHAR(10)     NOT NULL,
    Production_Order        VARCHAR(10)     NOT NULL,
    Furnace_ID              VARCHAR(12)     NOT NULL,
    Furnace_Type            VARCHAR(15)     NOT NULL,
    Treatment_Date          DATE            NOT NULL,
    Shift                   CHAR(1)         NOT NULL,
    Operator_ID             VARCHAR(10)     NOT NULL,
    Treatment_Type          VARCHAR(15)     NOT NULL,
    Product_Type            VARCHAR(20)     NOT NULL,
    Parts_Count             INTEGER         NOT NULL,
    Total_Load_Weight_KG    NUMERIC(10,1)   NOT NULL,
    Target_Temperature_C    NUMERIC(7,1)    NOT NULL,
    Actual_Temperature_C    NUMERIC(7,1)    NOT NULL,
    Heating_Rate_C_HR       NUMERIC(7,1)    NOT NULL,
    Holding_Time_Hours      NUMERIC(5,2)    NOT NULL,
    Cooling_Method          VARCHAR(15)     NOT NULL,
    Cooling_Rate_C_HR       NUMERIC(7,1)    NOT NULL,
    Atmosphere              VARCHAR(10)     NOT NULL DEFAULT 'AIR',
    Pre_HT_Hardness_HB      SMALLINT        NOT NULL,
    Post_HT_Hardness_HB     SMALLINT        NOT NULL,
    Hardness_Test_Location  VARCHAR(10)     NOT NULL,
    Microstructure          VARCHAR(25)     NOT NULL,
    Quality_Status          VARCHAR(10)     NOT NULL,
    Rejection_Reason        VARCHAR(40),
    Energy_Consumed_KWH     NUMERIC(10,1)   NOT NULL,
    Cycle_Time_Hours        NUMERIC(5,1)    NOT NULL,
    PRIMARY KEY (HT_Batch_Number)
);

CREATE TABLE machining_operations (
    Operation_ID            VARCHAR(12)     NOT NULL,
    Production_Order        VARCHAR(10)     NOT NULL,
    Operation_Date          DATE            NOT NULL,
    Work_Center             VARCHAR(8)      NOT NULL,
    Machine_ID              VARCHAR(12)     NOT NULL,
    Machine_Type            VARCHAR(30)     NOT NULL,
    Operation_Type          VARCHAR(25)     NOT NULL,
    Operator_ID             VARCHAR(10)     NOT NULL,
    Shift                   CHAR(1)         NOT NULL,
    Product_Type            VARCHAR(20)     NOT NULL,
    Operation_Sequence      INTEGER         NOT NULL,
    Tool_Material_Number    VARCHAR(10),
    Tool_Description        VARCHAR(60),
    Tool_Life_Used_Pct      NUMERIC(5,1),
    Spindle_Speed_RPM       INTEGER,
    Feed_Rate_MM_MIN        NUMERIC(8,1),
    Depth_Of_Cut_MM         NUMERIC(6,3),
    Coolant_Type            VARCHAR(15),
    Cycle_Time_Seconds      INTEGER,
    Setup_Time_Minutes      INTEGER,
    Tolerance_Upper_MM      NUMERIC(6,3),
    Tolerance_Lower_MM      NUMERIC(6,3),
    Measured_Deviation_MM   NUMERIC(6,3),
    Surface_Roughness_RA    NUMERIC(5,2),
    Quality_Status          VARCHAR(6)      NOT NULL,
    Defect_Type             VARCHAR(30),
    Power_Consumption_KW    NUMERIC(6,2),
    Quantity_Processed      INTEGER,
    PRIMARY KEY (Operation_ID)
);

CREATE TABLE quality_inspections (
    Inspection_Lot          VARCHAR(10)     NOT NULL,
    Inspection_Date         DATE            NOT NULL,
    Inspector_ID            VARCHAR(10)     NOT NULL,
    Inspection_Stage        VARCHAR(12)     NOT NULL,
    Material_Number         VARCHAR(20)     NOT NULL,
    Production_Order        VARCHAR(10)     NOT NULL,
    Casting_Batch           VARCHAR(10),
    Quantity_Inspected      INTEGER         NOT NULL,
    Sampling_Plan           VARCHAR(12)     NOT NULL,
    AQL_Level               NUMERIC(4,2)    NOT NULL,
    Visual_Inspection       VARCHAR(4)      NOT NULL,
    Dimensional_Check       VARCHAR(4)      NOT NULL,
    CMM_Measurement         VARCHAR(4)      NOT NULL,
    Hardness_HB             SMALLINT,
    Tensile_Strength_MPA    SMALLINT,
    Elongation_Pct          NUMERIC(4,1),
    NDT_Type                VARCHAR(20),
    NDT_Result              VARCHAR(4),
    Surface_Finish_RA       NUMERIC(5,2),
    Defect_Count            INTEGER         NOT NULL DEFAULT 0,
    Major_Defects           INTEGER         NOT NULL DEFAULT 0,
    Minor_Defects           INTEGER         NOT NULL DEFAULT 0,
    Critical_Defects        INTEGER         NOT NULL DEFAULT 0,
    Overall_Decision        VARCHAR(8)      NOT NULL,
    Rejection_Code          VARCHAR(10),
    Certificate_Number      VARCHAR(15),
    Inspection_Duration_Min INTEGER,
    PRIMARY KEY (Inspection_Lot)
);

CREATE TABLE inventory_movements (
    Document_Number         VARCHAR(12)     NOT NULL,
    Document_Date           DATE            NOT NULL,
    Posting_Date            DATE            NOT NULL,
    Movement_Type           VARCHAR(15)     NOT NULL,
    Movement_Code           SMALLINT        NOT NULL,
    Material_Number         VARCHAR(20)     NOT NULL,
    Material_Type           VARCHAR(30)     NOT NULL,
    Plant                   VARCHAR(10)     NOT NULL,
    Storage_Location        VARCHAR(10)     NOT NULL,
    From_Location           VARCHAR(10),
    To_Location             VARCHAR(10),
    Quantity                NUMERIC(14,3)   NOT NULL,
    Unit                    VARCHAR(5)      NOT NULL,
    Batch_Number            VARCHAR(15),
    Vendor_Number           VARCHAR(10),
    Purchase_Order          VARCHAR(12),
    Production_Order        VARCHAR(10),
    Cost_Center             VARCHAR(10),
    Amount_USD              NUMERIC(14,2)   NOT NULL,
    Currency                CHAR(3)         NOT NULL DEFAULT 'USD',
    User_ID                 VARCHAR(10)     NOT NULL,
    Stock_Before            NUMERIC(14,3)   NOT NULL,
    Stock_After             NUMERIC(14,3)   NOT NULL,
    PRIMARY KEY (Document_Number)
);

-- NOTE: Total_Cost_USD is a plain stored column (not GENERATED).
-- The CSV already contains the pre-computed value.
CREATE TABLE equipment_maintenance (
    Maintenance_Order       VARCHAR(10)     NOT NULL,
    Equipment_Number        VARCHAR(12)     NOT NULL,
    Equipment_Type          VARCHAR(30)     NOT NULL,
    Equipment_Description   VARCHAR(80)     NOT NULL,
    Plant                   VARCHAR(10)     NOT NULL,
    Work_Center             VARCHAR(10)     NOT NULL,
    Maintenance_Type        VARCHAR(15)     NOT NULL,
    Order_Type              VARCHAR(5)      NOT NULL,
    Priority                SMALLINT        NOT NULL,
    Planned_Start           TIMESTAMP       NOT NULL,
    Planned_End             TIMESTAMP       NOT NULL,
    Actual_Start            TIMESTAMP,
    Actual_End              TIMESTAMP,
    Status                  VARCHAR(12)     NOT NULL,
    Technician_ID           VARCHAR(10)     NOT NULL,
    Downtime_Hours          NUMERIC(6,1)    NOT NULL,
    Labor_Hours             NUMERIC(6,1)    NOT NULL,
    Parts_Cost_USD          NUMERIC(10,2)   NOT NULL DEFAULT 0,
    Labor_Cost_USD          NUMERIC(10,2)   NOT NULL DEFAULT 0,
    Total_Cost_USD          NUMERIC(10,2)   NOT NULL DEFAULT 0,
    Failure_Code            VARCHAR(6),
    Spare_Parts_Material    VARCHAR(10),
    Next_Maintenance_Due    DATE,
    Maintenance_Plan        VARCHAR(12),
    Notification_Number     VARCHAR(15)     NOT NULL,
    Created_By              VARCHAR(10)     NOT NULL,
    Created_Date            DATE            NOT NULL DEFAULT CURRENT_DATE,
    PRIMARY KEY (Maintenance_Order)
);


-- ================================================================
-- STEP 2 - IMPORT CSV FILES NOW IN THIS ORDER:
--   1. material_master          <- 01_Material_Master.csv
--   2. production_orders        <- 10_Production_Orders.csv
--   3. melting_heat_records     <- 03_Melting_Heat_Records.csv
--   4. molding_records          <- 04_Molding_Records.csv
--   5. casting_records          <- 05_Casting_Records.csv
--   6. heat_treatment           <- 06_Heat_Treatment.csv
--   7. machining_operations     <- 07_Machining_Operations.csv
--   8. quality_inspections      <- 08_Quality_Inspection.csv
--   9. inventory_movements      <- 09_Inventory_Movements.csv
--  10. bill_of_materials        <- 02_Bill_Of_Materials.csv
--  11. equipment_maintenance    <- 11_Equipment_Maintenance.csv
-- ================================================================


-- ================================================================
-- STEP 3 - ADD CONSTRAINTS (run ONLY after all imports succeed)
-- ================================================================

-- CHECK constraints
ALTER TABLE material_master
    ADD CONSTRAINT chk_mat_gross  CHECK (Gross_Weight_KG >= Net_Weight_KG),
    ADD CONSTRAINT chk_mat_price  CHECK (Standard_Price_USD >= 0),
    ADD CONSTRAINT chk_mat_abc    CHECK (ABC_Indicator IN ('A','B','C')),
    ADD CONSTRAINT chk_mat_proc   CHECK (Procurement_Type IN ('E','F')),
    ADD CONSTRAINT chk_mat_qi     CHECK (Quality_Inspection IN ('Y','N'));

ALTER TABLE production_orders
    ADD CONSTRAINT chk_po_status  CHECK (Order_Status IN ('CREATED','RELEASED','IN_PROCESS','COMPLETED','CLOSED')),
    ADD CONSTRAINT chk_po_alloy   CHECK (Alloy_Grade IN ('GG25','GG30','GG40')),
    ADD CONSTRAINT chk_po_product CHECK (Product_Type IN ('ENGINE_BLOCK','CYLINDER_HEAD','CYLINDER_LINER')),
    ADD CONSTRAINT chk_po_qty     CHECK (Order_Quantity > 0),
    ADD CONSTRAINT chk_po_dates   CHECK (Planned_End_Date >= Planned_Start_Date);

ALTER TABLE melting_heat_records
    ADD CONSTRAINT chk_heat_status CHECK (Quality_Status IN ('APPROVED','REJECTED')),
    ADD CONSTRAINT chk_heat_alloy  CHECK (Target_Alloy IN ('GG25','GG30','GG40')),
    ADD CONSTRAINT chk_heat_temps  CHECK (Pour_Temperature_C < Tap_Temperature_C),
    ADD CONSTRAINT chk_heat_tap    CHECK (Tap_Temperature_C BETWEEN 1400 AND 1600),
    ADD CONSTRAINT chk_heat_carbon CHECK (Carbon_Pct BETWEEN 2.8 AND 4.2);

ALTER TABLE molding_records
    ADD CONSTRAINT chk_mold_qc    CHECK (Quality_Check IN ('PASS','FAIL'));

ALTER TABLE casting_records
    ADD CONSTRAINT chk_cast_math  CHECK (Good_Castings + Scrap_Castings = Expected_Castings),
    ADD CONSTRAINT chk_cast_yield CHECK (Yield_Pct BETWEEN 0 AND 100),
    ADD CONSTRAINT chk_cast_grade CHECK (Quality_Grade IN ('A','B','C')),
    ADD CONSTRAINT chk_cast_filt  CHECK (Filter_Used IN ('YES','NO')),
    ADD CONSTRAINT chk_cast_inoc  CHECK (Inoculation_In_Ladle IN ('YES','NO'));

ALTER TABLE heat_treatment
    ADD CONSTRAINT chk_ht_status  CHECK (Quality_Status IN ('APPROVED','REWORK')),
    ADD CONSTRAINT chk_ht_type    CHECK (Treatment_Type IN ('STRESS_RELIEF','ANNEALING','NORMALIZING'));

ALTER TABLE machining_operations
    ADD CONSTRAINT chk_mach_status CHECK (Quality_Status IN ('PASS','FAIL'));

ALTER TABLE quality_inspections
    ADD CONSTRAINT chk_qi_decision CHECK (Overall_Decision IN ('ACCEPT','REJECT')),
    ADD CONSTRAINT chk_qi_stage    CHECK (Inspection_Stage IN ('INCOMING','IN_PROCESS','PATROL','FINAL')),
    ADD CONSTRAINT chk_qi_visual   CHECK (Visual_Inspection IN ('PASS','FAIL')),
    ADD CONSTRAINT chk_qi_dim      CHECK (Dimensional_Check IN ('PASS','FAIL'));

ALTER TABLE inventory_movements
    ADD CONSTRAINT chk_inv_mvtype  CHECK (Movement_Type IN ('GR_PURCHASE','GI_PRODUCTION','GR_PRODUCTION','TRANSFER','GI_SCRAP','RETURN_VENDOR')),
    ADD CONSTRAINT chk_inv_qty     CHECK (Quantity > 0),
    ADD CONSTRAINT chk_inv_amount  CHECK (Amount_USD >= 0),
    ADD CONSTRAINT chk_inv_stock   CHECK (Stock_Before >= 0 AND Stock_After >= 0);

ALTER TABLE equipment_maintenance
    ADD CONSTRAINT chk_maint_type  CHECK (Maintenance_Type IN ('PREVENTIVE','BREAKDOWN','INSPECTION','CORRECTIVE')),
    ADD CONSTRAINT chk_maint_order CHECK (Order_Type IN ('PM01','PM02','PM03','PM04')),
    ADD CONSTRAINT chk_maint_cost  CHECK (Parts_Cost_USD >= 0 AND Labor_Cost_USD >= 0 AND Total_Cost_USD >= 0),
    ADD CONSTRAINT chk_maint_dates CHECK (Planned_End > Planned_Start);

-- Foreign Key constraints
ALTER TABLE bill_of_materials
    ADD CONSTRAINT fk_bom_parent    FOREIGN KEY (Parent_Material)      REFERENCES material_master(Material_Number),
    ADD CONSTRAINT fk_bom_component FOREIGN KEY (Component_Material)   REFERENCES material_master(Material_Number);

ALTER TABLE production_orders
    ADD CONSTRAINT fk_po_material   FOREIGN KEY (Material_Number)      REFERENCES material_master(Material_Number);

ALTER TABLE molding_records
    ADD CONSTRAINT fk_mold_po       FOREIGN KEY (Production_Order)     REFERENCES production_orders(Production_Order);

ALTER TABLE casting_records
    ADD CONSTRAINT fk_cast_heat     FOREIGN KEY (Heat_Number)          REFERENCES melting_heat_records(Heat_Number),
    ADD CONSTRAINT fk_cast_po       FOREIGN KEY (Production_Order)     REFERENCES production_orders(Production_Order),
    ADD CONSTRAINT fk_cast_mold     FOREIGN KEY (Mold_Batch)           REFERENCES molding_records(Mold_Batch);

ALTER TABLE heat_treatment
    ADD CONSTRAINT fk_ht_casting    FOREIGN KEY (Casting_Batch)        REFERENCES casting_records(Casting_Batch),
    ADD CONSTRAINT fk_ht_po         FOREIGN KEY (Production_Order)     REFERENCES production_orders(Production_Order);

ALTER TABLE machining_operations
    ADD CONSTRAINT fk_mach_po       FOREIGN KEY (Production_Order)     REFERENCES production_orders(Production_Order),
    ADD CONSTRAINT fk_mach_tool     FOREIGN KEY (Tool_Material_Number) REFERENCES material_master(Material_Number);

ALTER TABLE quality_inspections
    ADD CONSTRAINT fk_qi_material   FOREIGN KEY (Material_Number)      REFERENCES material_master(Material_Number),
    ADD CONSTRAINT fk_qi_po         FOREIGN KEY (Production_Order)     REFERENCES production_orders(Production_Order),
    ADD CONSTRAINT fk_qi_casting    FOREIGN KEY (Casting_Batch)        REFERENCES casting_records(Casting_Batch);

ALTER TABLE inventory_movements
    ADD CONSTRAINT fk_inv_material  FOREIGN KEY (Material_Number)      REFERENCES material_master(Material_Number),
    ADD CONSTRAINT fk_inv_po        FOREIGN KEY (Production_Order)     REFERENCES production_orders(Production_Order);

ALTER TABLE equipment_maintenance
    ADD CONSTRAINT fk_maint_spare   FOREIGN KEY (Spare_Parts_Material) REFERENCES material_master(Material_Number);

-- Performance Indexes
CREATE INDEX idx_po_status      ON production_orders(Order_Status);
CREATE INDEX idx_po_product     ON production_orders(Product_Type);
CREATE INDEX idx_po_alloy       ON production_orders(Alloy_Grade);
CREATE INDEX idx_po_dates       ON production_orders(Planned_Start_Date, Planned_End_Date);
CREATE INDEX idx_po_customer    ON production_orders(Customer) WHERE Customer IS NOT NULL AND Customer <> '';

CREATE INDEX idx_heat_alloy     ON melting_heat_records(Target_Alloy);
CREATE INDEX idx_heat_date      ON melting_heat_records(Melt_Date);
CREATE INDEX idx_heat_status    ON melting_heat_records(Quality_Status);
CREATE INDEX idx_heat_furnace   ON melting_heat_records(Furnace_ID);

CREATE INDEX idx_mold_po        ON molding_records(Production_Order);
CREATE INDEX idx_mold_date      ON molding_records(Mold_Date);

CREATE INDEX idx_cast_heat      ON casting_records(Heat_Number);
CREATE INDEX idx_cast_po        ON casting_records(Production_Order);
CREATE INDEX idx_cast_date      ON casting_records(Casting_Date);
CREATE INDEX idx_cast_grade     ON casting_records(Quality_Grade);
CREATE INDEX idx_cast_product   ON casting_records(Product_Type);

CREATE INDEX idx_ht_casting     ON heat_treatment(Casting_Batch);
CREATE INDEX idx_ht_po          ON heat_treatment(Production_Order);
CREATE INDEX idx_ht_type        ON heat_treatment(Treatment_Type);

CREATE INDEX idx_mach_po        ON machining_operations(Production_Order);
CREATE INDEX idx_mach_date      ON machining_operations(Operation_Date);
CREATE INDEX idx_mach_status    ON machining_operations(Quality_Status);
CREATE INDEX idx_mach_product   ON machining_operations(Product_Type);

CREATE INDEX idx_qi_po          ON quality_inspections(Production_Order);
CREATE INDEX idx_qi_stage       ON quality_inspections(Inspection_Stage);
CREATE INDEX idx_qi_decision    ON quality_inspections(Overall_Decision);
CREATE INDEX idx_qi_date        ON quality_inspections(Inspection_Date);

CREATE INDEX idx_inv_mat        ON inventory_movements(Material_Number);
CREATE INDEX idx_inv_type       ON inventory_movements(Movement_Type);
CREATE INDEX idx_inv_po         ON inventory_movements(Production_Order) WHERE Production_Order IS NOT NULL;
CREATE INDEX idx_inv_date       ON inventory_movements(Posting_Date);

CREATE INDEX idx_maint_equip    ON equipment_maintenance(Equipment_Number);
CREATE INDEX idx_maint_type     ON equipment_maintenance(Maintenance_Type);
CREATE INDEX idx_maint_status   ON equipment_maintenance(Status);
CREATE INDEX idx_maint_due      ON equipment_maintenance(Next_Maintenance_Due);

-- Done
