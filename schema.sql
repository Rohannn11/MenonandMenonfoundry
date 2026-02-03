-- schema.sql
-- Complete DDL for the Foundry Digital Twin

CREATE TABLE IF NOT EXISTS material_master (
    "Material_Number" VARCHAR(50) PRIMARY KEY,
    "Material_Type" VARCHAR(50),
    "Description" TEXT,
    "Base_Unit" VARCHAR(10),
    "Procurement_Type" VARCHAR(1),
    "Standard_Price_USD" FLOAT
);

CREATE TABLE IF NOT EXISTS bill_of_materials (
    "BOM_Number" VARCHAR(50) PRIMARY KEY,
    "Parent_Material" VARCHAR(50),
    "Component_Material" VARCHAR(50),
    "Component_Quantity" FLOAT,
    "Component_Type" VARCHAR(50),
    "BOM_Status" VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS melting_heat_records (
    "Heat_Number" VARCHAR(50) PRIMARY KEY,
    "Furnace_ID" VARCHAR(20),
    "Tap_Temperature_C" FLOAT,
    "Target_Alloy" VARCHAR(50),
    "Carbon_Percentage" FLOAT,
    "Silicon_Percentage" FLOAT,
    "Quality_Status" VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS molding_records (
    "Production_Order" VARCHAR(50) PRIMARY KEY,
    "Molding_Line_ID" VARCHAR(20),
    "Molding_Type" VARCHAR(50),
    "Sand_Type" VARCHAR(50),
    "Mold_Hardness" FLOAT,
    "Defect_Type" VARCHAR(50),
    "Quality_Check" VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS casting_records (
    "Casting_Batch" VARCHAR(50) PRIMARY KEY,
    "Heat_Number" VARCHAR(50),
    "Product_Type" VARCHAR(50),
    "Pouring_Temperature_C" FLOAT,
    "Cooling_Time_Min" FLOAT,
    "Defects_Detected" VARCHAR(100),
    "Quality_Grade" VARCHAR(1)
);

CREATE TABLE IF NOT EXISTS heat_treatments (
    "HT_Batch_Number" VARCHAR(50) PRIMARY KEY,
    "Casting_Batch" VARCHAR(50),
    "Treatment_Type" VARCHAR(50),
    "Furnace_ID" VARCHAR(20),
    "Target_Temperature_C" FLOAT,
    "Actual_Temperature_C" FLOAT,
    "Quality_Status" VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS machining_operations (
    "Operation_ID" VARCHAR(50) PRIMARY KEY,
    "Casting_Batch" VARCHAR(50),
    "Machine_Type" VARCHAR(50),
    "Operation_Type" VARCHAR(50),
    "Cut_Speed_RPM" FLOAT,
    "Defect_Type" VARCHAR(50),
    "Quality_Status" VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS quality_inspections (
    "Inspection_Lot" VARCHAR(50) PRIMARY KEY,
    "Item_ID" VARCHAR(50),
    "Inspection_Stage" VARCHAR(50),
    "Defect_Count" INTEGER,
    "Defect_Code" VARCHAR(20),
    "Overall_Decision" VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS inventory_movements (
    "Document_Number" VARCHAR(50) PRIMARY KEY,
    "Material_Number" VARCHAR(50),
    "Movement_Type" VARCHAR(20),
    "Quantity" FLOAT,
    "Storage_Location" VARCHAR(20),
    "Movement_Date" DATE
);

CREATE TABLE IF NOT EXISTS production_orders (
    "Production_Order" VARCHAR(50) PRIMARY KEY,
    "Product_Type" VARCHAR(50),
    "Order_Quantity" INTEGER,
    "Start_Date" DATE,
    "End_Date" DATE,
    "Order_Status" VARCHAR(20),
    "Priority" INTEGER,
    "Planned_Costs_USD" FLOAT
);

CREATE TABLE IF NOT EXISTS equipment_maintenance (
    "Maintenance_Order" VARCHAR(50) PRIMARY KEY,
    "Equipment_ID" VARCHAR(20),
    "Equipment_Type" VARCHAR(50),
    "Maintenance_Type" VARCHAR(20),
    "Start_Date" DATE,
    "Status" VARCHAR(20),
    "Total_Cost_USD" FLOAT
);