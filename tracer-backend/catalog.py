"""Parts catalog for MCU breakout boards.

Every kicad_footprint is verified against KiCad 10.0 footprint libraries.
The search() interface is designed so a live distributor API can replace the
local table later without touching pipeline.py.
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CatalogPart:
    part_id: str
    category: str        # mcu|ldo|resistor|capacitor|sensor|connector|led|diode|crystal|header|inductor
    mpn: str             # manufacturer part number
    manufacturer: str
    description: str
    parameters: dict[str, Any]
    kicad_symbol: str    # Library:Symbol
    kicad_footprint: str # Library:Footprint
    available: bool = True
    # pins: pin_number -> {name, type}
    # type is one of: power_in|power_out|ground|bidir|input|output|passive|nc
    pins: dict[str, dict] = field(default_factory=dict)


# ── Hand-curated catalog for MCU breakout boards ──────────────────────────────
# Each footprint is verified to exist in KiCad 10.0 share/kicad/footprints/.

_CATALOG: list[CatalogPart] = [
    # ── MCUs ──────────────────────────────────────────────────────────────────
    CatalogPart(
        part_id="MCU_STM32F411CEU6",
        category="mcu",
        mpn="STM32F411CEU6",
        manufacturer="STMicroelectronics",
        description="ARM Cortex-M4 100 MHz 512 KB Flash 128 KB SRAM USB-FS QFN-48",
        parameters={
            "cpu": "Cortex-M4",
            "freq_mhz": 100,
            "flash_kb": 512,
            "ram_kb": 128,
            "gpio_count": 36,
            "i2c_count": 3,
            "spi_count": 5,
            "uart_count": 3,
            "usb_fs": 1,
            "adc_count": 1,
            "package": "QFN-48",
        },
        kicad_symbol="MCU_ST_STM32F4:STM32F411CEUx",
        kicad_footprint="Package_DFN_QFN:QFN-48-1EP_6x6mm_P0.4mm_EP4.2x4.2mm",
        pins={
            "1":  {"name": "VBAT",           "type": "power_in"},
            "5":  {"name": "OSC_IN",          "type": "input"},
            "6":  {"name": "OSC_OUT",         "type": "output"},
            "7":  {"name": "NRST",            "type": "input"},
            "12": {"name": "VSSA",            "type": "ground"},
            "13": {"name": "VDDA",            "type": "power_in"},
            "14": {"name": "PA0",             "type": "bidir"},
            "15": {"name": "PA1",             "type": "bidir"},
            "16": {"name": "PA2",             "type": "bidir"},
            "17": {"name": "PA3",             "type": "bidir"},
            "18": {"name": "PA4",             "type": "bidir"},
            "19": {"name": "PA5",             "type": "bidir"},
            "20": {"name": "PA6",             "type": "bidir"},
            "21": {"name": "PA7",             "type": "bidir"},
            "29": {"name": "PB6_I2C1_SCL",   "type": "bidir"},
            "30": {"name": "PB7_I2C1_SDA",   "type": "bidir"},
            "33": {"name": "PC6",             "type": "bidir"},
            "36": {"name": "PA8",             "type": "bidir"},
            "37": {"name": "PA9_TX",          "type": "bidir"},
            "38": {"name": "PA10_RX",         "type": "bidir"},
            "39": {"name": "PA11_USB_DM",     "type": "bidir"},
            "40": {"name": "PA12_USB_DP",     "type": "bidir"},
            "41": {"name": "PA13_SWDIO",      "type": "bidir"},
            "42": {"name": "VDD",             "type": "power_in"},
            "43": {"name": "PA14_SWCLK",      "type": "bidir"},
            "44": {"name": "PA15",            "type": "bidir"},
            "47": {"name": "PB3",             "type": "bidir"},
            "48": {"name": "PB4",             "type": "bidir"},
            "EP": {"name": "EP_GND",          "type": "ground"},
        },
    ),
    CatalogPart(
        part_id="MCU_STM32F103C8T6",
        category="mcu",
        mpn="STM32F103C8T6",
        manufacturer="STMicroelectronics",
        description="ARM Cortex-M3 72 MHz 64 KB Flash 20 KB SRAM USB-FS LQFP-48",
        parameters={
            "cpu": "Cortex-M3",
            "freq_mhz": 72,
            "flash_kb": 64,
            "ram_kb": 20,
            "gpio_count": 37,
            "i2c_count": 2,
            "spi_count": 2,
            "uart_count": 3,
            "usb_fs": 1,
            "adc_count": 2,
            "package": "LQFP-48",
        },
        kicad_symbol="MCU_ST_STM32F1:STM32F103C8Tx",
        kicad_footprint="Package_QFP:LQFP-48_7x7mm_P0.5mm",
        pins={
            "1":  {"name": "VBAT",         "type": "power_in"},
            "5":  {"name": "OSC_IN",        "type": "input"},
            "6":  {"name": "OSC_OUT",       "type": "output"},
            "7":  {"name": "NRST",          "type": "input"},
            "8":  {"name": "VSSA",          "type": "ground"},
            "9":  {"name": "VDDA",          "type": "power_in"},
            "10": {"name": "PA0",           "type": "bidir"},
            "11": {"name": "PA1",           "type": "bidir"},
            "12": {"name": "PA2",           "type": "bidir"},
            "13": {"name": "PA3",           "type": "bidir"},
            "14": {"name": "PA4",           "type": "bidir"},
            "15": {"name": "PA5",           "type": "bidir"},
            "16": {"name": "PA6",           "type": "bidir"},
            "17": {"name": "PA7",           "type": "bidir"},
            "18": {"name": "PB0",           "type": "bidir"},
            "19": {"name": "PB1",           "type": "bidir"},
            "20": {"name": "BOOT1_PB2",     "type": "bidir"},
            "21": {"name": "PB10_I2C2_SCL", "type": "bidir"},
            "22": {"name": "PB11_I2C2_SDA", "type": "bidir"},
            "23": {"name": "VSS_1",         "type": "ground"},
            "24": {"name": "VDD_1",         "type": "power_in"},
            "34": {"name": "PA9_TX",        "type": "bidir"},
            "35": {"name": "PA10_RX",       "type": "bidir"},
            "36": {"name": "PA11_USB_DM",   "type": "bidir"},
            "37": {"name": "PA12_USB_DP",   "type": "bidir"},
            "38": {"name": "PA13_SWDIO",    "type": "bidir"},
            "39": {"name": "VSS_2",         "type": "ground"},
            "40": {"name": "VDD_2",         "type": "power_in"},
            "41": {"name": "PA14_SWCLK",    "type": "bidir"},
            "42": {"name": "PA15",          "type": "bidir"},
            "46": {"name": "PD2",           "type": "bidir"},
            "47": {"name": "PB3",           "type": "bidir"},
            "48": {"name": "PB4",           "type": "bidir"},
        },
    ),
    CatalogPart(
        part_id="MCU_ATSAMD21G18A",
        category="mcu",
        mpn="ATSAMD21G18A-AUT",
        manufacturer="Microchip",
        description="ARM Cortex-M0+ 48 MHz 256 KB Flash 32 KB SRAM USB-FS TQFP-48",
        parameters={
            "cpu": "Cortex-M0+",
            "freq_mhz": 48,
            "flash_kb": 256,
            "ram_kb": 32,
            "gpio_count": 38,
            "i2c_count": 6,
            "spi_count": 6,
            "uart_count": 6,
            "usb_fs": 1,
            "adc_count": 1,
            "package": "TQFP-48",
        },
        kicad_symbol="MCU_Microchip_SAMD:ATSAMD21G18A-xUT",
        kicad_footprint="Package_QFP:LQFP-48_7x7mm_P0.5mm",
        pins={
            "1":  {"name": "PA0",          "type": "bidir"},
            "2":  {"name": "PA1",          "type": "bidir"},
            "3":  {"name": "PA2",          "type": "bidir"},
            "4":  {"name": "PA3",          "type": "bidir"},
            "7":  {"name": "PA4",          "type": "bidir"},
            "8":  {"name": "PA5",          "type": "bidir"},
            "9":  {"name": "PA6",          "type": "bidir"},
            "10": {"name": "PA7",          "type": "bidir"},
            "11": {"name": "PA8_SDA",      "type": "bidir"},
            "12": {"name": "PA9_SCL",      "type": "bidir"},
            "21": {"name": "PA16_SWCLK",   "type": "bidir"},
            "22": {"name": "PA17_SWDIO",   "type": "bidir"},
            "23": {"name": "PA18",         "type": "bidir"},
            "24": {"name": "PA19",         "type": "bidir"},
            "25": {"name": "PA20",         "type": "bidir"},
            "26": {"name": "PA21",         "type": "bidir"},
            "27": {"name": "PA22_SDA",     "type": "bidir"},
            "28": {"name": "PA23_SCL",     "type": "bidir"},
            "29": {"name": "PA24_USB_DM",  "type": "bidir"},
            "30": {"name": "PA25_USB_DP",  "type": "bidir"},
            "36": {"name": "PA27",         "type": "bidir"},
            "38": {"name": "RESET",        "type": "input"},
            "39": {"name": "PA28",         "type": "bidir"},
            "41": {"name": "PA30_SWCLK",   "type": "bidir"},
            "42": {"name": "PA31_SWDIO",   "type": "bidir"},
            "43": {"name": "PB0",          "type": "bidir"},
            "44": {"name": "PB1",          "type": "bidir"},
            "45": {"name": "PB2",          "type": "bidir"},
            "46": {"name": "PB3",          "type": "bidir"},
            "5":  {"name": "VDDANA",       "type": "power_in"},
            "6":  {"name": "GND_ANA",      "type": "ground"},
            "13": {"name": "GND_1",        "type": "ground"},
            "14": {"name": "VDD_1",        "type": "power_in"},
            "32": {"name": "GND_2",        "type": "ground"},
            "33": {"name": "VDD_2",        "type": "power_in"},
            "47": {"name": "GND_3",        "type": "ground"},
            "48": {"name": "VDD_3",        "type": "power_in"},
        },
    ),

    # ── LDO Regulators ────────────────────────────────────────────────────────
    CatalogPart(
        part_id="LDO_AMS1117_3V3",
        category="ldo",
        mpn="AMS1117-3.3",
        manufacturer="Advanced Monolithic Systems",
        description="3.3 V 1 A LDO SOT-223",
        parameters={
            "output_voltage_v": 3.3,
            "max_current_a": 1.0,
            "dropout_v": 1.3,
            "input_voltage_max_v": 15.0,
            "quiescent_current_ma": 10.0,
            "package": "SOT-223",
        },
        kicad_symbol="Regulator_Linear:AMS1117-3.3",
        kicad_footprint="Package_TO_SOT_SMD:SOT-223-3_TabPin2",
        # SOT-223-3: pin1=GND/adj, pin2=VOUT (tab), pin3=VIN
        pins={
            "1": {"name": "GND",  "type": "ground"},
            "2": {"name": "VOUT", "type": "power_out"},
            "3": {"name": "VIN",  "type": "power_in"},
        },
    ),
    CatalogPart(
        part_id="LDO_AP2112K_3V3",
        category="ldo",
        mpn="AP2112K-3.3TRG1",
        manufacturer="Diodes Incorporated",
        description="3.3 V 600 mA LDO with enable SOT-23-5",
        parameters={
            "output_voltage_v": 3.3,
            "max_current_a": 0.6,
            "dropout_v": 0.34,
            "input_voltage_max_v": 6.0,
            "quiescent_current_ma": 0.055,
            "package": "SOT-23-5",
        },
        kicad_symbol="Regulator_Linear:AP2112K-3.3",
        kicad_footprint="Package_TO_SOT_SMD:SOT-23-5",
        # SOT-23-5: pin1=EN, pin2=GND, pin3=VIN, pin4=VOUT, pin5=NC
        pins={
            "1": {"name": "EN",   "type": "input"},
            "2": {"name": "GND",  "type": "ground"},
            "3": {"name": "VIN",  "type": "power_in"},
            "4": {"name": "VOUT", "type": "power_out"},
            "5": {"name": "NC",   "type": "nc"},
        },
    ),
    CatalogPart(
        part_id="LDO_MCP1700_3V3",
        category="ldo",
        mpn="MCP1700T-3302E/TT",
        manufacturer="Microchip",
        description="3.3 V 250 mA ultra-low IQ (2 µA) LDO SOT-23",
        parameters={
            "output_voltage_v": 3.3,
            "max_current_a": 0.25,
            "dropout_v": 0.178,
            "input_voltage_max_v": 6.0,
            "quiescent_current_ma": 0.002,
            "package": "SOT-23",
        },
        kicad_symbol="Regulator_Linear:MCP1700T-3302E_TT",
        kicad_footprint="Package_TO_SOT_SMD:SOT-23",
        # SOT-23: pin1=GND, pin2=VOUT, pin3=VIN
        pins={
            "1": {"name": "GND",  "type": "ground"},
            "2": {"name": "VOUT", "type": "power_out"},
            "3": {"name": "VIN",  "type": "power_in"},
        },
    ),

    # ── Capacitors ────────────────────────────────────────────────────────────
    CatalogPart(
        part_id="CAP_100N_0402",
        category="capacitor",
        mpn="GCM155R71H104KA55D",
        manufacturer="Murata",
        description="100 nF 50 V X7R 0402 decoupling",
        parameters={
            "capacitance_uf": 0.1,
            "voltage_v": 50,
            "dielectric": "X7R",
            "package": "0402",
            "tolerance_pct": 10,
        },
        kicad_symbol="Device:C",
        kicad_footprint="Capacitor_SMD:C_0402_1005Metric",
        pins={"1": {"name": "~", "type": "passive"}, "2": {"name": "~", "type": "passive"}},
    ),
    CatalogPart(
        part_id="CAP_1U_0402",
        category="capacitor",
        mpn="GCM155R71A105KE38D",
        manufacturer="Murata",
        description="1 µF 10 V X5R 0402 bypass",
        parameters={
            "capacitance_uf": 1.0,
            "voltage_v": 10,
            "dielectric": "X5R",
            "package": "0402",
            "tolerance_pct": 10,
        },
        kicad_symbol="Device:C",
        kicad_footprint="Capacitor_SMD:C_0402_1005Metric",
        pins={"1": {"name": "~", "type": "passive"}, "2": {"name": "~", "type": "passive"}},
    ),
    CatalogPart(
        part_id="CAP_4U7_0402",
        category="capacitor",
        mpn="GCM155R71A475KE58D",
        manufacturer="Murata",
        description="4.7 µF 10 V X5R 0402 bulk bypass",
        parameters={
            "capacitance_uf": 4.7,
            "voltage_v": 10,
            "dielectric": "X5R",
            "package": "0402",
            "tolerance_pct": 20,
        },
        kicad_symbol="Device:C",
        kicad_footprint="Capacitor_SMD:C_0402_1005Metric",
        pins={"1": {"name": "~", "type": "passive"}, "2": {"name": "~", "type": "passive"}},
    ),
    CatalogPart(
        part_id="CAP_10U_0805",
        category="capacitor",
        mpn="GRT21BR61C106KE01L",
        manufacturer="Murata",
        description="10 µF 16 V X5R 0805 bulk input/output",
        parameters={
            "capacitance_uf": 10.0,
            "voltage_v": 16,
            "dielectric": "X5R",
            "package": "0805",
            "tolerance_pct": 20,
        },
        kicad_symbol="Device:C",
        kicad_footprint="Capacitor_SMD:C_0805_2012Metric",
        pins={"1": {"name": "~", "type": "passive"}, "2": {"name": "~", "type": "passive"}},
    ),
    CatalogPart(
        part_id="CAP_22P_0402",
        category="capacitor",
        mpn="GCM1555C1H220JA16D",
        manufacturer="Murata",
        description="22 pF 50 V C0G 0402 crystal load",
        parameters={
            "capacitance_uf": 0.000022,
            "voltage_v": 50,
            "dielectric": "C0G",
            "package": "0402",
            "tolerance_pct": 5,
        },
        kicad_symbol="Device:C",
        kicad_footprint="Capacitor_SMD:C_0402_1005Metric",
        pins={"1": {"name": "~", "type": "passive"}, "2": {"name": "~", "type": "passive"}},
    ),
    CatalogPart(
        part_id="CAP_100P_0402",
        category="capacitor",
        mpn="GCM1555C1H101JA16D",
        manufacturer="Murata",
        description="100 pF 50 V C0G 0402 general RF/filter",
        parameters={
            "capacitance_uf": 0.0001,
            "voltage_v": 50,
            "dielectric": "C0G",
            "package": "0402",
            "tolerance_pct": 5,
        },
        kicad_symbol="Device:C",
        kicad_footprint="Capacitor_SMD:C_0402_1005Metric",
        pins={"1": {"name": "~", "type": "passive"}, "2": {"name": "~", "type": "passive"}},
    ),

    # ── Resistors ─────────────────────────────────────────────────────────────
    CatalogPart(
        part_id="RES_10K_0402",
        category="resistor",
        mpn="CRCW040210K0FKED",
        manufacturer="Vishay",
        description="10 kΩ 1 % 63 mW 0402 general pull-up/down",
        parameters={
            "resistance_ohm": 10000,
            "tolerance_pct": 1,
            "power_w": 0.063,
            "package": "0402",
        },
        kicad_symbol="Device:R",
        kicad_footprint="Resistor_SMD:R_0402_1005Metric",
        pins={"1": {"name": "~", "type": "passive"}, "2": {"name": "~", "type": "passive"}},
    ),
    CatalogPart(
        part_id="RES_4K7_0402",
        category="resistor",
        mpn="CRCW04024K70FKED",
        manufacturer="Vishay",
        description="4.7 kΩ 1 % 63 mW 0402 I²C pull-up",
        parameters={
            "resistance_ohm": 4700,
            "tolerance_pct": 1,
            "power_w": 0.063,
            "package": "0402",
        },
        kicad_symbol="Device:R",
        kicad_footprint="Resistor_SMD:R_0402_1005Metric",
        pins={"1": {"name": "~", "type": "passive"}, "2": {"name": "~", "type": "passive"}},
    ),
    CatalogPart(
        part_id="RES_1K_0402",
        category="resistor",
        mpn="CRCW04021K00FKED",
        manufacturer="Vishay",
        description="1 kΩ 1 % 63 mW 0402 LED current limiter",
        parameters={
            "resistance_ohm": 1000,
            "tolerance_pct": 1,
            "power_w": 0.063,
            "package": "0402",
        },
        kicad_symbol="Device:R",
        kicad_footprint="Resistor_SMD:R_0402_1005Metric",
        pins={"1": {"name": "~", "type": "passive"}, "2": {"name": "~", "type": "passive"}},
    ),
    CatalogPart(
        part_id="RES_33R_0402",
        category="resistor",
        mpn="CRCW040233R0FKED",
        manufacturer="Vishay",
        description="33 Ω 1 % 63 mW 0402 USB DP/DM series termination",
        parameters={
            "resistance_ohm": 33,
            "tolerance_pct": 1,
            "power_w": 0.063,
            "package": "0402",
        },
        kicad_symbol="Device:R",
        kicad_footprint="Resistor_SMD:R_0402_1005Metric",
        pins={"1": {"name": "~", "type": "passive"}, "2": {"name": "~", "type": "passive"}},
    ),
    CatalogPart(
        part_id="RES_100R_0402",
        category="resistor",
        mpn="CRCW0402100RFKED",
        manufacturer="Vishay",
        description="100 Ω 1 % 63 mW 0402 general purpose",
        parameters={
            "resistance_ohm": 100,
            "tolerance_pct": 1,
            "power_w": 0.063,
            "package": "0402",
        },
        kicad_symbol="Device:R",
        kicad_footprint="Resistor_SMD:R_0402_1005Metric",
        pins={"1": {"name": "~", "type": "passive"}, "2": {"name": "~", "type": "passive"}},
    ),

    # ── I²C Sensors ───────────────────────────────────────────────────────────
    CatalogPart(
        part_id="SENSOR_BME280",
        category="sensor",
        mpn="BME280",
        manufacturer="Bosch Sensortec",
        description="Temp/humidity/pressure sensor I²C+SPI LGA-8 2.5×2.5 mm",
        parameters={
            "interface": "I2C",
            "interface_alt": "SPI",
            "measures": "temperature,humidity,pressure",
            "supply_v_min": 1.71,
            "supply_v_max": 3.6,
            "package": "LGA-8",
        },
        kicad_symbol="Sensor_Atmospheric:BME280",
        kicad_footprint="Package_LGA:Bosch_LGA-8_2.5x2.5mm_P0.65mm_ClockwisePinNumbering",
        # BME280 LGA-8: 1=GND, 2=CSB, 3=SDI/SDA, 4=SCK/SCL, 5=SDO, 6=GND, 7=VDDIO, 8=VDD
        pins={
            "1": {"name": "GND",     "type": "ground"},
            "2": {"name": "CSB",     "type": "input"},
            "3": {"name": "SDI_SDA", "type": "bidir"},
            "4": {"name": "SCK_SCL", "type": "bidir"},
            "5": {"name": "SDO",     "type": "input"},
            "6": {"name": "GND2",    "type": "ground"},
            "7": {"name": "VDDIO",   "type": "power_in"},
            "8": {"name": "VDD",     "type": "power_in"},
        },
    ),
    CatalogPart(
        part_id="SENSOR_MPU6050",
        category="sensor",
        mpn="MPU-6050",
        manufacturer="InvenSense",
        description="6-axis IMU accel+gyro I²C QFN-24 4×4 mm",
        parameters={
            "interface": "I2C",
            "measures": "acceleration,gyroscope",
            "supply_v_min": 2.375,
            "supply_v_max": 3.46,
            "package": "QFN-24",
        },
        kicad_symbol="Sensor_Motion:MPU-6050",
        kicad_footprint="Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm",
        # MPU-6050 QFN-24 key structural pins
        pins={
            "1":  {"name": "CLKIN",   "type": "input"},
            "2":  {"name": "GND",     "type": "ground"},
            "3":  {"name": "REGOUT",  "type": "output"},
            "4":  {"name": "FSYNC",   "type": "bidir"},
            "5":  {"name": "INT",     "type": "output"},
            "6":  {"name": "VDD",     "type": "power_in"},
            "7":  {"name": "CPOUT",   "type": "passive"},
            "8":  {"name": "VLOGIC",  "type": "power_in"},
            "9":  {"name": "AD0",     "type": "input"},
            "10": {"name": "AUX_SDA", "type": "bidir"},
            "11": {"name": "AUX_SCL", "type": "bidir"},
            "20": {"name": "GND2",    "type": "ground"},
            "21": {"name": "GND3",    "type": "ground"},
            "22": {"name": "nCS",     "type": "input"},
            "23": {"name": "SCL",     "type": "bidir"},
            "24": {"name": "SDA",     "type": "bidir"},
            "EP": {"name": "EP_GND",  "type": "ground"},
        },
    ),
    CatalogPart(
        part_id="SENSOR_SHT31",
        category="sensor",
        mpn="SHT31-DIS-B",
        manufacturer="Sensirion",
        description="High-accuracy temp/humidity sensor I²C DFN-8 2×2 mm",
        parameters={
            "interface": "I2C",
            "measures": "temperature,humidity",
            "temp_accuracy_c": 0.2,
            "rh_accuracy_pct": 2,
            "supply_v_min": 2.4,
            "supply_v_max": 5.5,
            "package": "DFN-8",
        },
        kicad_symbol="Sensor_Humidity:SHT31-DIS",
        kicad_footprint="Package_DFN_QFN:DFN-8_2x2mm_P0.5mm",
        # SHT31 DFN-8: 1=SDA, 2=ADDR, 3=ALERT, 4=SCL, 5=VDD, 6=nRESET, 7=NC, 8=GND
        pins={
            "1": {"name": "SDA",    "type": "bidir"},
            "2": {"name": "ADDR",   "type": "input"},
            "3": {"name": "ALERT",  "type": "output"},
            "4": {"name": "SCL",    "type": "bidir"},
            "5": {"name": "VDD",    "type": "power_in"},
            "6": {"name": "nRESET", "type": "input"},
            "7": {"name": "NC",     "type": "nc"},
            "8": {"name": "GND",    "type": "ground"},
        },
    ),

    # ── USB Connectors ────────────────────────────────────────────────────────
    CatalogPart(
        part_id="CONN_USB_C_GCT4085",
        category="connector",
        mpn="USB4085-GF-A",
        manufacturer="GCT",
        description="USB-C 2.0 receptacle mid-mount SMD 5 A 20 V",
        parameters={
            "connector_type": "USB-C",
            "usb_version": "2.0",
            "mounting": "SMD",
            "current_rating_a": 5,
            "voltage_rating_v": 20,
        },
        kicad_symbol="Connector:USB_C_Receptacle_USB2.0",
        kicad_footprint="Connector_USB:USB_C_Receptacle_GCT_USB4085",
        # USB-C receptacle USB 2.0: VBUS (5 V from host), GND, D+, D-, CC1, CC2
        pins={
            "A1":  {"name": "GND",  "type": "ground"},
            "A4":  {"name": "VBUS", "type": "power_in"},
            "A5":  {"name": "CC1",  "type": "bidir"},
            "A6":  {"name": "DP1",  "type": "bidir"},
            "A7":  {"name": "DM1",  "type": "bidir"},
            "A12": {"name": "GND2", "type": "ground"},
            "B1":  {"name": "GND3", "type": "ground"},
            "B4":  {"name": "VBUS2","type": "power_in"},
            "B5":  {"name": "CC2",  "type": "bidir"},
            "B6":  {"name": "DP2",  "type": "bidir"},
            "B7":  {"name": "DM2",  "type": "bidir"},
            "B12": {"name": "GND4", "type": "ground"},
        },
    ),
    CatalogPart(
        part_id="CONN_USB_C_GCT4110",
        category="connector",
        mpn="USB4110-GF-A",
        manufacturer="GCT",
        description="USB-C 2.0 receptacle horizontal low-profile SMD 5 A 20 V",
        parameters={
            "connector_type": "USB-C",
            "usb_version": "2.0",
            "mounting": "SMD",
            "current_rating_a": 5,
            "voltage_rating_v": 20,
        },
        kicad_symbol="Connector:USB_C_Receptacle_USB2.0",
        kicad_footprint="Connector_USB:USB_C_Receptacle_GCT_USB4110",
        pins={
            "A1":  {"name": "GND",  "type": "ground"},
            "A4":  {"name": "VBUS", "type": "power_in"},
            "A5":  {"name": "CC1",  "type": "bidir"},
            "A6":  {"name": "DP1",  "type": "bidir"},
            "A7":  {"name": "DM1",  "type": "bidir"},
            "A12": {"name": "GND2", "type": "ground"},
            "B1":  {"name": "GND3", "type": "ground"},
            "B4":  {"name": "VBUS2","type": "power_in"},
            "B5":  {"name": "CC2",  "type": "bidir"},
            "B6":  {"name": "DP2",  "type": "bidir"},
            "B7":  {"name": "DM2",  "type": "bidir"},
            "B12": {"name": "GND4", "type": "ground"},
        },
    ),

    # ── LEDs ──────────────────────────────────────────────────────────────────
    CatalogPart(
        part_id="LED_RED_0603",
        category="led",
        mpn="KPHHS-1005SURCK",
        manufacturer="Kingbright",
        description="Red LED 620 nm Vf 2.0 V 0603",
        parameters={
            "color": "red",
            "wavelength_nm": 620,
            "vf_v": 2.0,
            "if_ma": 20,
            "package": "0603",
        },
        kicad_symbol="Device:LED",
        kicad_footprint="LED_SMD:LED_0603_1608Metric",
        pins={"A": {"name": "A", "type": "passive"}, "K": {"name": "K", "type": "passive"}},
    ),
    CatalogPart(
        part_id="LED_GREEN_0603",
        category="led",
        mpn="KPHHS-1005SGCK",
        manufacturer="Kingbright",
        description="Green LED 525 nm Vf 2.1 V 0603",
        parameters={
            "color": "green",
            "wavelength_nm": 525,
            "vf_v": 2.1,
            "if_ma": 20,
            "package": "0603",
        },
        kicad_symbol="Device:LED",
        kicad_footprint="LED_SMD:LED_0603_1608Metric",
        pins={"A": {"name": "A", "type": "passive"}, "K": {"name": "K", "type": "passive"}},
    ),
    CatalogPart(
        part_id="LED_RED_0402",
        category="led",
        mpn="APT1608SURCK",
        manufacturer="Kingbright",
        description="Red LED 620 nm Vf 2.1 V 0402 compact",
        parameters={
            "color": "red",
            "wavelength_nm": 620,
            "vf_v": 2.1,
            "if_ma": 20,
            "package": "0402",
        },
        kicad_symbol="Device:LED",
        kicad_footprint="LED_SMD:LED_0402_1005Metric",
        pins={"A": {"name": "A", "type": "passive"}, "K": {"name": "K", "type": "passive"}},
    ),

    # ── Crystals ──────────────────────────────────────────────────────────────
    CatalogPart(
        part_id="XTAL_8MHZ_3225",
        category="crystal",
        mpn="ABM8AIG-8.000MHZ-4-1Z-T3",
        manufacturer="Abracon",
        description="8 MHz SMD crystal ±10 ppm 18 pF load 3.2×2.5 mm",
        parameters={
            "frequency_mhz": 8.0,
            "frequency_tolerance_ppm": 10,
            "load_capacitance_pf": 18,
            "esr_ohm": 60,
            "package": "SMD-3225-4",
        },
        kicad_symbol="Device:Crystal_GND24",
        kicad_footprint="Crystal:Crystal_SMD_Abracon_ABM8AIG-4Pin_3.2x2.5mm",
        # 4-pin SMD crystal: 1=XIN, 2=GND, 3=XOUT, 4=GND (Crystal_GND24 symbol)
        pins={
            "1": {"name": "XIN",  "type": "passive"},
            "2": {"name": "GND1", "type": "ground"},
            "3": {"name": "XOUT", "type": "passive"},
            "4": {"name": "GND2", "type": "ground"},
        },
    ),
    CatalogPart(
        part_id="XTAL_12MHZ_3225",
        category="crystal",
        mpn="TSX-3225 12.0000MF09Z-AC0",
        manufacturer="Seiko Epson",
        description="12 MHz SMD crystal ±10 ppm 9 pF load 3.2×2.5 mm",
        parameters={
            "frequency_mhz": 12.0,
            "frequency_tolerance_ppm": 10,
            "load_capacitance_pf": 9,
            "esr_ohm": 50,
            "package": "SMD-3225-4",
        },
        kicad_symbol="Device:Crystal_GND24",
        kicad_footprint="Crystal:Crystal_SMD_SeikoEpson_TSX3225-4Pin_3.2x2.5mm",
        pins={
            "1": {"name": "XIN",  "type": "passive"},
            "2": {"name": "GND1", "type": "ground"},
            "3": {"name": "XOUT", "type": "passive"},
            "4": {"name": "GND2", "type": "ground"},
        },
    ),

    # ── ESD / Schottky Diodes ─────────────────────────────────────────────────
    CatalogPart(
        part_id="DIODE_ESD_USBLC6",
        category="diode",
        mpn="USBLC6-2SC6",
        manufacturer="STMicroelectronics",
        description="Dual USB ESD protection 6.8 V clamp 0.5 pF SOT-23-6",
        parameters={
            "type": "ESD",
            "channels": 2,
            "clamping_voltage_v": 6.8,
            "capacitance_pf": 0.5,
            "package": "SOT-23-6",
        },
        kicad_symbol="ESD_Protection:USBLC6-2SC6",
        kicad_footprint="Package_TO_SOT_SMD:SOT-23-6",
        # USBLC6-2SC6 SOT-23-6: 1=IO1_DM, 2=GND, 3=VCC, 4=IO2_DP, 5=VCC, 6=GND
        pins={
            "1": {"name": "IO1_DM", "type": "bidir"},
            "2": {"name": "GND",    "type": "ground"},
            "3": {"name": "VCC",    "type": "power_in"},
            "4": {"name": "IO2_DP", "type": "bidir"},
            "5": {"name": "VCC2",   "type": "power_in"},
            "6": {"name": "GND2",   "type": "ground"},
        },
    ),
    CatalogPart(
        part_id="DIODE_SCHOTTKY_BAT60",
        category="diode",
        mpn="BAT60JFILM",
        manufacturer="STMicroelectronics",
        description="Schottky diode 10 V 1.6 A Vf 0.35 V SOT-23",
        parameters={
            "type": "Schottky",
            "vf_v": 0.35,
            "vr_v": 10,
            "if_a": 1.6,
            "package": "SOT-23",
        },
        kicad_symbol="Device:D_Schottky",
        kicad_footprint="Package_TO_SOT_SMD:SOT-23",
        # BAT60JFILM SOT-23: pin1=A, pin2=A, pin3=K
        pins={
            "1": {"name": "A", "type": "passive"},
            "2": {"name": "A2","type": "passive"},
            "3": {"name": "K", "type": "passive"},
        },
    ),

    # ── Pin Headers ───────────────────────────────────────────────────────────
    CatalogPart(
        part_id="HEADER_1X20_2V54",
        category="header",
        mpn="PH-1-20-UA",
        manufacturer="Adam Tech",
        description="1×20 2.54 mm male pin header vertical THT breakout",
        parameters={
            "pins": 20,
            "pitch_mm": 2.54,
            "rows": 1,
            "gender": "male",
            "mounting": "THT",
        },
        kicad_symbol="Connector_Generic:Conn_01x20",
        kicad_footprint="Connector_PinHeader_2.54mm:PinHeader_1x20_P2.54mm_Vertical",
        pins={str(i): {"name": f"Pin{i}", "type": "passive"} for i in range(1, 21)},
    ),
    CatalogPart(
        part_id="HEADER_2X05_2V54",
        category="header",
        mpn="67997-210HLF",
        manufacturer="Amphenol",
        description="2×05 2.54 mm male shrouded header SWD/JTAG debug THT",
        parameters={
            "pins": 10,
            "pitch_mm": 2.54,
            "rows": 2,
            "gender": "male",
            "mounting": "THT",
        },
        kicad_symbol="Connector_Generic:Conn_02x05_Odd_Even",
        kicad_footprint="Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical",
        pins={str(i): {"name": f"Pin{i}", "type": "passive"} for i in range(1, 11)},
    ),

    # ── Ferrite Beads ─────────────────────────────────────────────────────────
    CatalogPart(
        part_id="FERRITE_600R_0402",
        category="inductor",
        mpn="BLM15AX601SN1D",
        manufacturer="Murata",
        description="600 Ω @ 100 MHz 500 mA 0402 ferrite bead power filtering",
        parameters={
            "impedance_ohm_at_100mhz": 600,
            "dc_resistance_ohm": 0.45,
            "current_rating_a": 0.5,
            "package": "0402",
        },
        kicad_symbol="Device:Ferrite_Bead",
        kicad_footprint="Inductor_SMD:L_0402_1005Metric",
        pins={"1": {"name": "~", "type": "passive"}, "2": {"name": "~", "type": "passive"}},
    ),
]


# ── Public API ────────────────────────────────────────────────────────────────

def search(category: str, criteria: dict[str, Any]) -> list[CatalogPart]:
    """Return all available catalog parts in *category* that satisfy *criteria*.

    *criteria* maps parameter names to constraint specs:
      - ``{"eq": v}``           exact equality (numeric with 0.01 % tolerance)
      - ``{"min": v}``          numeric >= v
      - ``{"max": v}``          numeric <= v
      - ``{"min": v1, "max": v2}``  range
      - ``{"in": [v1, v2, ...]}``   set membership (case-insensitive strings)
      - scalar value            treated as eq

    Parameters absent from a part's parameter dict are silently skipped so that
    the same criteria can match parts whose catalogs are less detailed.
    """
    results = []
    for part in _CATALOG:
        if part.category != category:
            continue
        if not part.available:
            continue
        if _matches(part.parameters, criteria):
            results.append(part)
    return results


def get_part(part_id: str) -> Optional[CatalogPart]:
    for p in _CATALOG:
        if p.part_id == part_id:
            return p
    return None


def get_pins(part_id: str) -> dict[str, dict]:
    """Return the pin map for a part, or {} if the part is unknown."""
    p = get_part(part_id)
    return p.pins if p else {}


def all_parts() -> list[CatalogPart]:
    return list(_CATALOG)


# ── Internal matching logic ───────────────────────────────────────────────────

def _matches(params: dict[str, Any], criteria: dict[str, Any]) -> bool:
    for key, constraint in criteria.items():
        if key not in params:
            continue  # missing param: skip rather than fail
        actual = params[key]

        if isinstance(constraint, dict):
            if "eq" in constraint:
                if not _eq(actual, constraint["eq"]):
                    return False
            if "min" in constraint:
                try:
                    if float(actual) < float(constraint["min"]):
                        return False
                except (TypeError, ValueError):
                    return False
            if "max" in constraint:
                try:
                    if float(actual) > float(constraint["max"]):
                        return False
                except (TypeError, ValueError):
                    return False
            if "in" in constraint:
                vals = constraint["in"]
                if isinstance(vals, str):
                    vals = [v.strip() for v in vals.split(",")]
                if not any(_eq(actual, v) for v in vals):
                    return False
        else:
            if not _eq(actual, constraint):
                return False
    return True


def _eq(a: Any, b: Any) -> bool:
    """Numeric equality with 0.01 % tolerance; string equality is case-insensitive."""
    try:
        fa, fb = float(a), float(b)
        return abs(fa - fb) <= 1e-9 + 1e-4 * abs(fb)
    except (TypeError, ValueError):
        return str(a).strip().lower() == str(b).strip().lower()


# ── Footprint geometry (courtyard bbox + key pin offsets from center) ─────────
# bbox_mm: (width, height) at rotation=0 — courtyard/keepout boundary.
# pins_mm: {pin_number → (dx_mm, dy_mm)} from component center at rotation=0.
#   Only key electrical pins are listed; unlisted pins use (0, 0) by default.
#   Coordinate system: x right, y down (matches PCB/KiCad screen convention).
#
# Source: KiCad 10.0 library courtyards + package datasheet nominal dimensions.

_GEOMETRY: dict[str, dict] = {
    # ── MCUs ─────────────────────────────────────────────────────────────────
    # QFN-48-1EP_6x6mm_P0.4mm: body 6×6, courtyard 7.5×7.5
    # Pad centres: ±3.1 mm from package centre; 12 pads/side at 0.4 mm pitch
    # Bottom (y=+3.1): pins 1-12, x = -2.2 … +2.2
    # Left   (x=−3.1): pins 13-24, y = +2.2 … −2.2
    # Top    (y=−3.1): pins 25-36, x = +2.2 … −2.2
    # Right  (x=+3.1): pins 37-48, y = −2.2 … +2.2
    "MCU_STM32F411CEU6": {
        "bbox_mm": (7.5, 7.5),
        "pins_mm": {
            "5":  (-0.6,  3.1),   # OSC_IN   (bottom, i=4)
            "6":  (-0.2,  3.1),   # OSC_OUT  (bottom, i=5)
            "12": ( 2.2,  3.1),   # VSSA     (bottom, i=11)
            "13": (-3.1,  2.2),   # VDDA     (left,   i=0)
            "29": ( 0.6, -3.1),   # PB6_SCL  (top,    i=4)
            "30": ( 0.2, -3.1),   # PB7_SDA  (top,    i=5)
            "39": ( 3.1, -1.4),   # USB_DM   (right,  i=2)
            "40": ( 3.1, -1.0),   # USB_DP   (right,  i=3)
            "42": ( 3.1, -0.2),   # VDD      (right,  i=5)
            "EP": ( 0.0,  0.0),   # EP_GND   (exposed pad centre)
        },
    },
    # LQFP-48_7x7mm_P0.5mm: body 7×7, lead tip ~4.5 mm, courtyard 11×11
    # 12 pads/side at 0.5 mm pitch spanning ±2.75 mm; pad centre at ±4.5 mm
    # Bottom (y=+4.5): pins 1-12, x = -2.75 … +2.75
    # Left   (x=−4.5): pins 13-24, y = +2.75 … −2.75
    # Top    (y=−4.5): pins 25-36, x = +2.75 … −2.75
    # Right  (x=+4.5): pins 37-48, y = −2.75 … +2.75
    "MCU_STM32F103C8T6": {
        "bbox_mm": (11.0, 11.0),
        "pins_mm": {
            "5":  (-0.75,  4.5),  # OSC_IN   (bottom, i=4)
            "6":  (-0.25,  4.5),  # OSC_OUT  (bottom, i=5)
            "8":  ( 0.75,  4.5),  # VSSA     (bottom, i=7)
            "9":  ( 1.25,  4.5),  # VDDA     (bottom, i=8)
            "21": (-4.5,  -1.25), # PB10_SCL (left,   i=8)
            "22": (-4.5,  -1.75), # PB11_SDA (left,   i=9)
            "23": (-4.5,  -2.25), # VSS_1    (left,   i=10)
            "24": (-4.5,  -2.75), # VDD_1    (left,   i=11)
            "36": (-2.75, -4.5),  # USB_DM   (top,    i=11)
            "37": ( 4.5,  -2.75), # USB_DP   (right,  i=0)
            "39": ( 4.5,  -1.75), # VSS_2    (right,  i=2)
            "40": ( 4.5,  -1.25), # VDD_2    (right,  i=3)
        },
    },
    "MCU_ATSAMD21G18A": {
        "bbox_mm": (11.0, 11.0),
        "pins_mm": {
            "5":  (-3.25,  4.5),  # VDDANA (bottom, i=4 — pin 5)
            "6":  (-2.75,  4.5),  # GND_ANA
            "11": (-4.5,   1.75), # PA8_SDA (left, i=2)
            "12": (-4.5,   1.25), # PA9_SCL (left, i=3)
            "13": (-4.5,   0.75), # GND_1
            "14": (-4.5,   0.25), # VDD_1
            "29": ( 0.75, -4.5),  # PA24_USB_DM (top, i=8)
            "30": ( 1.25, -4.5),  # PA25_USB_DP (top, i=9)
            "32": ( 4.5,   1.75), # GND_2 (right, i=10)
            "33": ( 4.5,   2.25), # VDD_2 (right, i=11)
            "47": (-4.5,  -2.25), # GND_3 (left, i=10)
            "48": (-4.5,  -2.75), # VDD_3 (left, i=11)
        },
    },

    # ── LDO Regulators ───────────────────────────────────────────────────────
    # SOT-223-3_TabPin2: body ~6.5×3.5, courtyard ~7.0×4.0
    "LDO_AMS1117_3V3": {
        "bbox_mm": (7.0, 4.0),
        "pins_mm": {
            "1": (-2.3, 1.5),  # GND
            "2": ( 0.0, 1.5),  # VOUT (tab)
            "3": ( 2.3, 1.5),  # VIN
        },
    },
    # SOT-23-5: ~2.9×1.6mm body, courtyard ~3.5×2.2
    "LDO_AP2112K_3V3": {
        "bbox_mm": (3.5, 2.2),
        "pins_mm": {
            "1": (-0.95,  0.95),  # EN
            "2": ( 0.0,   0.95),  # GND
            "3": ( 0.95,  0.95),  # VIN
            "4": ( 0.475,-0.95),  # VOUT
        },
    },
    # SOT-23: ~2.9×1.3mm body, courtyard ~3.0×2.0
    "LDO_MCP1700_3V3": {
        "bbox_mm": (3.0, 2.0),
        "pins_mm": {
            "1": (-0.95, 0.8),   # GND
            "2": ( 0.0, -0.8),   # VOUT
            "3": ( 0.95, 0.8),   # VIN
        },
    },

    # ── Capacitors (all passives: center is adequate for proximity) ───────────
    "CAP_100N_0402":  {"bbox_mm": (2.0, 1.2), "pins_mm": {}},
    "CAP_1U_0402":    {"bbox_mm": (2.0, 1.2), "pins_mm": {}},
    "CAP_4U7_0402":   {"bbox_mm": (2.0, 1.2), "pins_mm": {}},
    "CAP_10U_0805":   {"bbox_mm": (3.2, 2.2), "pins_mm": {}},
    "CAP_22P_0402":   {"bbox_mm": (2.0, 1.2), "pins_mm": {}},
    "CAP_100P_0402":  {"bbox_mm": (2.0, 1.2), "pins_mm": {}},

    # ── Resistors ─────────────────────────────────────────────────────────────
    "RES_10K_0402":   {"bbox_mm": (2.0, 1.2), "pins_mm": {}},
    "RES_4K7_0402":   {"bbox_mm": (2.0, 1.2), "pins_mm": {}},
    "RES_1K_0402":    {"bbox_mm": (2.0, 1.2), "pins_mm": {}},
    "RES_33R_0402":   {"bbox_mm": (2.0, 1.2), "pins_mm": {}},
    "RES_100R_0402":  {"bbox_mm": (2.0, 1.2), "pins_mm": {}},

    # ── I²C Sensors ───────────────────────────────────────────────────────────
    # Bosch_LGA-8_2.5x2.5mm: body 2.5×2.5, courtyard ~3.5×3.5
    "SENSOR_BME280": {
        "bbox_mm": (3.5, 3.5),
        "pins_mm": {
            "3": (-1.0, 0.0),   # SDI_SDA
            "4": ( 1.0, 0.0),   # SCK_SCL
            "7": ( 0.0,-1.0),   # VDDIO
            "8": ( 0.0,-1.0),   # VDD  (same side, approximate)
            "1": ( 0.0, 1.0),   # GND
        },
    },
    # QFN-24-1EP_4x4mm: body 4×4, courtyard ~5.5×5.5
    # 6 pads/side at 0.5mm pitch spanning ±1.25mm; pad centre at ±2.3mm
    "SENSOR_MPU6050": {
        "bbox_mm": (5.5, 5.5),
        "pins_mm": {
            "6":  (-2.3, -1.25), # VDD  (left, i=1)
            "8":  (-2.3, -0.25), # VLOGIC (left, i=3)
            "23": ( 2.3,  0.25), # SCL (right, i=... approx)
            "24": ( 2.3,  0.75), # SDA
            "EP": ( 0.0,  0.0),  # EP_GND
        },
    },
    # DFN-8_2x2mm: body 2×2, courtyard ~3.0×3.0
    "SENSOR_SHT31": {
        "bbox_mm": (3.0, 3.0),
        "pins_mm": {
            "1": (-1.0, 0.5),   # SDA
            "4": ( 1.0, 0.5),   # SCL
            "5": ( 1.0,-0.5),   # VDD
            "8": (-1.0,-0.5),   # GND
        },
    },

    # ── USB Connectors (edge-mount) ────────────────────────────────────────────
    # USB4085-GF-A: ~9.5×8.5mm overall courtyard
    "CONN_USB_C_GCT4085": {"bbox_mm": (9.5, 8.5), "pins_mm": {}},
    # USB4110-GF-A: horizontal low-profile ~10.5×9.5mm
    "CONN_USB_C_GCT4110": {"bbox_mm": (10.5, 9.5), "pins_mm": {}},

    # ── LEDs ──────────────────────────────────────────────────────────────────
    "LED_RED_0603":   {"bbox_mm": (2.2, 1.5), "pins_mm": {}},
    "LED_GREEN_0603": {"bbox_mm": (2.2, 1.5), "pins_mm": {}},
    "LED_RED_0402":   {"bbox_mm": (2.0, 1.2), "pins_mm": {}},

    # ── Crystals ──────────────────────────────────────────────────────────────
    # 3.2×2.5mm body, courtyard ~4.5×3.5mm
    "XTAL_8MHZ_3225":  {"bbox_mm": (4.5, 3.5), "pins_mm": {}},
    "XTAL_12MHZ_3225": {"bbox_mm": (4.5, 3.5), "pins_mm": {}},

    # ── ESD / Schottky Diodes ─────────────────────────────────────────────────
    # SOT-23-6: ~2.9×1.6mm body, courtyard ~3.5×2.5
    "DIODE_ESD_USBLC6":     {"bbox_mm": (3.5, 2.5), "pins_mm": {}},
    # SOT-23: courtyard ~3.0×2.0
    "DIODE_SCHOTTKY_BAT60": {"bbox_mm": (3.0, 2.0), "pins_mm": {}},

    # ── Pin Headers ───────────────────────────────────────────────────────────
    # 1×20 2.54mm THT: 20 pins × 2.54mm = 50.8mm long, ~3.5mm wide (with courtyard)
    "HEADER_1X20_2V54": {"bbox_mm": (52.0, 3.5), "pins_mm": {}},
    # 2×05 2.54mm THT: 5×2.54=12.7mm × 2×2.54+2=7.1mm
    "HEADER_2X05_2V54": {"bbox_mm": (14.0, 7.5), "pins_mm": {}},

    # ── Ferrite Bead ──────────────────────────────────────────────────────────
    "FERRITE_600R_0402": {"bbox_mm": (2.0, 1.2), "pins_mm": {}},
}


def get_geometry(part_id: str) -> Optional[dict]:
    """Return geometry dict with bbox_mm and pins_mm, or None if unknown.

    bbox_mm: (width_mm, height_mm) courtyard at rotation=0.
    pins_mm: {pin_number → (dx_mm, dy_mm)} offset from component centre.
    """
    return _GEOMETRY.get(part_id)
