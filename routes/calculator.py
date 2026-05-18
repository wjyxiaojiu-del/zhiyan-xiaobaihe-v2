"""试剂计算器路由"""
import math
from flask import Blueprint, render_template, request, jsonify
from data.reagent_db import MW_DB

calc_bp = Blueprint("calculator", __name__)


@calc_bp.route("/calculator")
def calculator():
    return render_template("calculator.html", mw_db=MW_DB)


@calc_bp.route("/api/calculate", methods=["POST"])
def api_calculate():
    data = request.json
    calc_type = data.get("type")

    try:
        if calc_type == "molarity_to_mass":
            mw = float(data["mw"])
            molarity = float(data["molarity"])
            volume = float(data["volume"])
            mass_g = molarity * mw * (volume / 1000)
            return jsonify({
                "mass_g": round(mass_g, 4),
                "mass_mg": round(mass_g * 1000, 2),
                "volume": volume,
            })

        elif calc_type == "mass_to_molarity":
            mw = float(data["mw"])
            mass = float(data["mass"])
            volume = float(data["volume"])
            molarity = mass / (mw * volume / 1000)
            return jsonify({
                "molarity_mol": round(molarity, 6),
                "molarity_mmol": round(molarity * 1000, 4),
                "mass_conc": round(mass * 1000 / volume, 4),
            })

        elif calc_type == "dilution":
            stock = float(data["stock"])
            target = float(data["target"])
            volume = float(data["volume"])
            if stock < target:
                return jsonify({"error": "母液浓度必须大于目标浓度"})
            vol_stock = (target * volume) / stock
            vol_solvent = volume - vol_stock
            return jsonify({
                "vol_stock_ml": round(vol_stock, 4),
                "vol_stock_ul": round(vol_stock * 1000, 2),
                "vol_solvent": round(vol_solvent, 4),
                "dilution_ratio": round(stock / target, 2),
            })

        elif calc_type == "gradient":
            start = float(data["start"])
            factor = float(data["factor"])
            steps = int(data["steps"])
            vol = float(data["vol"])
            result = []
            for i in range(steps + 1):
                conc = start / (factor ** i)
                if i == 0:
                    result.append({"level": f"第{i}级(原液)", "conc": round(conc, 6), "method": f"取原液 {vol}mL"})
                else:
                    vs = (conc * vol) / start
                    vx = vol - vs
                    result.append({
                        "level": f"第{i}级(稀释{factor**i:.0f}倍)",
                        "conc": round(conc, 6),
                        "method": f"取原液 {round(vs*1000,2)}uL + 溶剂 {round(vx,3)}mL",
                    })
            return jsonify({"table": result})

        elif calc_type == "rpm_rcf":
            mode = data["mode"]
            radius = float(data["radius"])
            if mode == "rpm_to_rcf":
                rpm = float(data["value"])
                rcf = 1.118e-5 * radius * rpm ** 2
                return jsonify({"result": round(rcf, 2), "unit": "xg"})
            else:
                rcf = float(data["value"])
                rpm = math.sqrt(rcf / (1.118e-5 * radius))
                return jsonify({"result": round(rpm, 0), "unit": "rpm"})

        elif calc_type == "reconstitution":
            mass_mg = float(data["mass"])
            conc_mg_ml = float(data["conc"])
            mw = float(data["mw"]) if data.get("mw") else 0
            volume_ml = mass_mg / conc_mg_ml if conc_mg_ml != 0 else 0
            result = {
                "volume_ml": round(volume_ml, 4),
                "volume_ul": round(volume_ml * 1000, 2),
            }
            if mw > 0:
                molarity = (mass_mg / (mw * 1000)) / (volume_ml / 1000) if volume_ml > 0 else 0
                result["molarity_mmol"] = round(molarity * 1000, 4)
            return jsonify(result)

        elif calc_type == "specific_activity":
            ed50 = float(data["ed50"])
            mw = float(data.get("mw", 0))
            if ed50 <= 0:
                return jsonify({"error": "ED50必须大于0"})
            sa = 1e6 / ed50
            result = {"sa_unit_mg": round(sa, 4)}
            if mw > 0:
                sa_mol = 1e6 / (ed50 * mw)
                result["sa_nmol_mg"] = round(sa_mol, 4)
            return jsonify(result)

        return jsonify({"error": "未知计算类型"})

    except (ValueError, KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {str(e)}"}), 400
    except ZeroDivisionError:
        return jsonify({"error": "除零错误，请检查输入参数"}), 400
