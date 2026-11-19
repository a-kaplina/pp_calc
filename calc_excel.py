import io
from datetime import datetime

import pandas as pd
import streamlit as st
from openpyxl.styles import Font

st.set_page_config(page_title="Расчёт ПП у детей", layout="wide")
st.markdown(
    """
    <style>
    div[data-testid="stMetricValue"] > div {
        font-size: 24px !important;
    }
    div[data-testid="stMetricLabel"] > div {
        font-size: 24px !important;
    }
    div[data-testid="stMetricDelta"] > div {
        font-size: 14px !important;
    }
     div[data-testid="stHeading"] h2 { font-size: 22px !important; }
    div[data-testid="stHeading"] h3 { font-size: 22px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Калькулятор парентерального питания")

MIXES = {
    "НАН ГА":   {"kcal": 67.0, "protein": 1.27, "fat": 3.40, "carb": 7.78, "lactose": 7.78},
    "преНАН0":  {"kcal": 80.0, "protein": 2.90, "fat": 3.99, "carb": 8.12, "lactose": 3.69},
    "преНАН 1": {"kcal": 72.5, "protein": 2.10, "fat": 3.80, "carb": 7.77, "lactose": 3.80},
}


def calc_pp(m, dose_liq, dose_alb, dose_fat, SpeedC,
            FPK, FPCa, DoseNa, DoseMg,
            dose_sol_per_kg, dose_vit_per_kg,
            C1, C2, v_enter_calc):
    if C2 < C1 or m <= 0:
        return None
    daily_dose_liq = m * dose_liq
    daily_dose_parent_eat = daily_dose_liq - v_enter_calc
    daily_dose_alb = m * dose_alb
    daily_dose_amino_10 = daily_dose_alb * 10
    daily_dose_fat = m * dose_fat
    daily_dose_emulsion_fat_20 = daily_dose_fat * 5
    K = FPK * m * 1.85
    Ca = FPCa * m / 100
    Na = m * DoseNa / 1.7
    Mg = m * DoseMg / 250
    Sol = m * dose_sol_per_kg
    Vit = m * dose_vit_per_kg
    dose_gluc = SpeedC * m * 1.44
    v_gluc = (daily_dose_liq - daily_dose_amino_10 - daily_dose_emulsion_fat_20
              - K - Ca - Na - Mg - Sol - Vit - v_enter_calc)
    if C2 == C1:
        dose_gluc_C1 = v_gluc
        dose_gluc_C2 = 0.0
    else:
        denom = (C2 - C1)
        dose_gluc_C2 = (dose_gluc * 100 - v_gluc * C1) / denom
        dose_gluc_C1 = v_gluc - dose_gluc_C2
    concentrate_gluc = (dose_gluc * 100 / v_gluc) if v_gluc > 0 else float("nan")
    pp_protein = daily_dose_alb
    pp_fat = daily_dose_fat
    pp_carb = dose_gluc
    return {
        "daily_dose_liq": daily_dose_liq,
        "daily_dose_parent_eat": daily_dose_parent_eat,
        "daily_dose_alb": daily_dose_alb,
        "daily_dose_amino_10": daily_dose_amino_10,
        "daily_dose_fat": daily_dose_fat,
        "daily_dose_emulsion_fat_20": daily_dose_emulsion_fat_20,
        "K": K, "Ca": Ca, "Na": Na, "Mg": Mg,
        "Sol": Sol, "Vit": Vit,
        "dose_gluc": dose_gluc,
        "v_gluc": v_gluc,
        "dose_gluc_C1": dose_gluc_C1,
        "dose_gluc_C2": dose_gluc_C2,
        "concentrate_gluc": concentrate_gluc,
        "pp_protein": pp_protein,
        "pp_fat": pp_fat,
        "pp_carb": pp_carb,
    }


with st.form("pp_form"):
    st.subheader("Энтеральное питание")
    chosen_mix_name = st.selectbox("Смесь", options=list(MIXES.keys()), index=0)
    mix = MIXES[chosen_mix_name]
    st.caption(
        f"Состав на 100 мл: {mix['kcal']:.1f} ккал • белок {mix['protein']:.1f} г • "
        f"жир {mix['fat']:.1f} г • углеводы {mix['carb']:.1f} г • лактоза {mix['lactose']:.1f} г"
    )

    ec1, ec2 = st.columns(2)
    with ec1:
        m = st.number_input("Масса ребёнка, кг", min_value=0.1, value=3.0, step=0.1)
        vol_per_feed = st.number_input("Объём одного кормления, мл", min_value=0.0, value=0.0, step=5.0)
    with ec2:
        n_feeds = st.number_input("Кратность кормлений в сутки", min_value=1, max_value=12, value=7, step=1)

    st.markdown("**Объёмы кормлений, мл (заполните первые N по кратности):**")
    feed_volumes = []
    feed_cols = st.columns(n_feeds)
    for i in range(7):
        col = feed_cols[i % n_feeds]
        disabled = i >= n_feeds
        v = col.number_input(
            f"№{i+1}",
            min_value=vol_per_feed,
            value=0.0 if disabled else float(vol_per_feed),
            step=5.0,
            key=f"feed_{i}",
            disabled=disabled,
        )
        if not disabled:
            feed_volumes.append(v)

    total_enter_ml = sum(feed_volumes)
    dose_enter_per_kg = total_enter_ml / m if m > 0 else 0.0

    enter_kcal    = total_enter_ml * mix["kcal"]    / 100 / m
    enter_protein = total_enter_ml * mix["protein"] / 100 / m
    enter_fat     = total_enter_ml * mix["fat"]     / 100 / m
    enter_carb    = total_enter_ml * mix["carb"]    / 100 / m
    enter_lactose = total_enter_ml * mix["lactose"] / 100 / m

    st.caption(
        f"Суточный объём ЭП: **{total_enter_ml:.1f} мл**  •  "
        f"ЭП: **{dose_enter_per_kg:.1f} мл/кг/сут**  ({total_enter_ml:.1f} мл / {m:.1f} кг)"
    )
    st.markdown(
        f"**Из ЭП за сутки (на кг):** {enter_kcal:.1f} ккал/кг • "
        f"белок {enter_protein:.2f} г/кг • жир {enter_fat:.2f} г/кг • "
        f"углеводы {enter_carb:.2f} г/кг • лактоза {enter_lactose:.2f} г/кг"
    )
    if dose_enter_per_kg < 25:
        st.caption("⚠️ Объём питания трофический (< 25 мл/кг/сут), не будет учитываться при расчёте объёма инфузии.")

    st.divider()
    st.subheader("Парентеральное питание")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Основное")
        dose_liq = st.number_input("Объем жидкости (общий), мл/кг/сут", min_value=0.0, value=100.0, step=10.0)
    with col2:
        st.subheader("Нутриенты")
        dose_alb = st.number_input("Доза белка, г/кг/сут", min_value=0.0, value=1.0, step=0.5)
        dose_fat = st.number_input("Доза жира, г/кг/сут", min_value=0.0, value=0.0, step=0.5)
        SpeedC = st.number_input("Скорость введения углеводов, мг/кг/мин", min_value=0.0, value=4.0, step=0.1)
    with col3:
        st.subheader("Электролиты")
        FPK = st.number_input("ФП калий, ммоль/кг/сут", min_value=0.0, value=0.0, step=0.5)
        FPCa = st.number_input("ФП кальций, мг/кг/сут", min_value=0.0, value=100.0, step=50.0)
        DoseNa = st.number_input("Доза натрия, ммоль/кг/сут", min_value=0.0, value=0.0, step=0.5)
        DoseMg = st.number_input("Доза магния, мг/кг/сут", min_value=0.0, value=0.0, step=50.0)
        st.caption("⚠️ Растворы магния и кальция нельзя смешивать в одной капельнице - возможно выпадение осадка")

    st.divider()
    col4, col5, col6 = st.columns(3)
    with col4:
        st.subheader("Солувит")
        dose_sol_per_kg = st.number_input("Доза Солувита, мл/кг/сут", min_value=0.0, value=0.0, step=1.0)
    with col5:
        st.subheader("Виталипид")
        dose_vit_per_kg = st.number_input("Доза Виталипида, мл/кг/сут", min_value=0.0, value=0.0, step=2.0)
    with col6:
        st.subheader("Глюкоза (C1/C2)")
        C1 = st.number_input("C1, %", min_value=0.0, value=5.0, step=5.0)
        C2 = st.number_input("C2, %", min_value=0.0, value=20.0, step=5.0)
        st.caption("Если есть только один раствор — установите C1 = C2.")

    # Сводка ЭП+ПП
    st.divider()
    st.markdown("### Потребляемые Ккал и нутриенты (ЭП + ПП)")
    v_enter_calc_preview = total_enter_ml if dose_enter_per_kg >= 25 else 0.0
    pp_preview = calc_pp(m, dose_liq, dose_alb, dose_fat, SpeedC,
                         FPK, FPCa, DoseNa, DoseMg,
                         dose_sol_per_kg, dose_vit_per_kg,
                         C1, C2, v_enter_calc_preview)

    if pp_preview is None:
        st.warning("Проверьте C1/C2 и массу — предварительный расчёт ПП невозможен.")
    else:
        parenter_kcal = dose_alb * 4 + dose_fat * 9 + SpeedC * 1.44 * 3.4
        parenter_carb = SpeedC * 1.44
        total_kcal    = enter_kcal    + parenter_kcal
        total_protein = enter_protein + dose_alb
        total_fat     = enter_fat     + dose_fat
        total_carb    = enter_carb    + parenter_carb

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Ккал / кг (ЭП+ПП)", f"{total_kcal:.1f}")
        s2.metric("Белок, г / кг (ЭП+ПП)", f"{total_protein:.1f}")
        s3.metric("Жир, г / кг (ЭП+ПП)", f"{total_fat:.1f}")
        s4.metric("Углеводы, г / кг (ЭП+ПП)", f"{total_carb:.1f}")

        st.caption(
            f"ЭП: {enter_kcal:.1f} ккал/кг / Б {enter_protein:.1f} / Ж {enter_fat:.1f} / У {enter_carb:.1f} (г/кг)  •  "
            f"ПП: {parenter_kcal:.1f} ккал/кг / Б {dose_alb:.1f} / Ж {dose_fat:.1f} / У {parenter_carb:.1f} (г/кг)"
        )

    submitted = st.form_submit_button("Рассчитать", type="primary")


# Результаты
if submitted:
    errors = []
    if C2 < C1:
        errors.append("C2 не может быть меньше C1.")
    if m <= 0:
        errors.append("Масса должна быть > 0.")

    v_enter_calc = total_enter_ml if dose_enter_per_kg >= 25 else 0.0
    res = calc_pp(m, dose_liq, dose_alb, dose_fat, SpeedC,
                  FPK, FPCa, DoseNa, DoseMg,
                  dose_sol_per_kg, dose_vit_per_kg,
                  C1, C2, v_enter_calc)

    if res is None:
        for e in (errors or ["Проверьте C1/C2 и массу."]):
            st.error(e)
    else:
        v_gluc = res["v_gluc"]
        dose_gluc_C1 = res["dose_gluc_C1"]
        dose_gluc_C2 = res["dose_gluc_C2"]
        concentrate_gluc = res["concentrate_gluc"]
        daily_dose_parent_eat = res["daily_dose_parent_eat"]

        if v_gluc < 0:
            st.error(f"Объём глюкозы отрицательный ({v_gluc:.1f} мл). Уменьшите дозы/объёмы других компонентов.")
        if dose_gluc_C1 < 0 or dose_gluc_C2 < 0:
            st.warning("Один из объёмов глюкозы (C1/C2) отрицательный — проверьте C1/C2 и общий объём.")
        if daily_dose_parent_eat < 0:
            st.warning("Объём ПП отрицательный: энтеральное питание превышает общий объём жидкости.")
        if v_gluc > 0 and not (min(C1, C2) <= concentrate_gluc <= max(C1, C2)):
            st.warning(
                f"Требуемая концентрация глюкозы {concentrate_gluc:.1f}% выходит за диапазон "
                f"растворов [{C1:.1f}%; {C2:.1f}%]. Нужен раствор другой концентрации."
            )

        st.info(f"Смесь: {chosen_mix_name}")

        st.subheader("Результаты")
        st.caption("Для профилактики тромбоза катетера в раствор следует добавлять гепарин. Доза гепарина может определяться либо из расчета 0,5–1 ЕД на 1 мл. готового раствора, либо 25–30 ЕД на килограмм массы тела в сут.")
        st.caption("Жировые эмульсии готовятся в отдельном флаконе или шприце без добавления гепарина.")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### Расчетные объёмы")
            st.metric("Общий объём жидкости, мл", f"{res['daily_dose_liq']:.1f}")
            st.metric("Объём ПП, мл", f"{daily_dose_parent_eat:.1f}")
            st.metric("Объём ЭП (учитываемый), мл", f"{v_enter_calc:.1f}")
            st.metric("Объём глюкозы, мл", f"{v_gluc:.1f}")
            st.metric("Концентрация общ. р-ра глюкозы, %", f"{concentrate_gluc:.1f}")
        with c2:
            st.markdown("#### Объемы растворов, мл")
            if C2 == C1:
                st.metric(f"Раствор {C1:.1f}%, мл", f"{v_gluc:.1f}")
                st.caption(f"Проверка УН и концентрации по растворам: {(dose_gluc_C1 * C1 * 10) / 24 / 60 / m:.1f} мг/кг/мин, {(dose_gluc_C1 * C1 * 10) / v_gluc / 10:.1f} %")
            else:
                st.metric(f"Раствор C1 (Sol. Glucosae {int(C1)}%), мл", f"{dose_gluc_C1:.1f}")
                st.metric(f"Раствор C2 (Sol. Glucosae {int(C2)} %), мл", f"{dose_gluc_C2:.1f}")
                st.caption(
                    f"Проверка УН и концентрации по растворам: {(dose_gluc_C1 * C1 + dose_gluc_C2 * C2) * 10 / 24 / 60 / m:.1f} мг/кг/мин, {(dose_gluc_C1 * C1 * 10 + dose_gluc_C2 * C2 * 10) / v_gluc / 10:.1f} %")
            st.metric("Белок (Аминовен Инфант 10%), мл", f"{res['daily_dose_amino_10']:.1f}")
            st.metric("Калий (Sol. KCl 4%)", f"{res['K']:.1f}")
            st.metric("Натрий (Sol. NaCl 10%)", f"{res['Na']:.1f}")
            st.metric("Кальций (Sol. Ca gluconatis 10%)", f"{res['Ca']:.1f}")
            st.metric("Магний (Sol. MgSO4 25%)", f"{res['Mg']:.1f}")
            st.metric("Солувит", f"{res['Sol']:.1f}")
            sol_rate = (dose_gluc_C1 + dose_gluc_C2 + res["daily_dose_amino_10"] + res["K"] + res["Ca"] + res["Mg"] + res["Sol"]) / 24
            st.metric("Скорость глюкозы и электролитов, мл/ч", f"{sol_rate:.1f}")
            
        with c3:
            st.markdown("#### Жиры, мл")
            st.metric("Жировая эмульсия 20%, мл", f"{res['daily_dose_emulsion_fat_20']:.1f}")
            st.metric("Виталипид", f"{res['Vit']:.1f}")
            vit_rate = (res['daily_dose_emulsion_fat_20'] + res['Vit']) / 24
            st.metric("Скорость жиров, мл/ч", f"{vit_rate:.1f}")
            

        with st.expander("Показать все расчётные значения"):
            st.write({
                "Смесь": chosen_mix_name,
                "Масса, кг": m,
                "Объёмы кормлений, мл": feed_volumes,
                "Суточный объём ЭП, мл": total_enter_ml,
                "Доза ЭП, мл/кг/сут": dose_enter_per_kg,
                "v_enter_calc (учитываемый), мл": v_enter_calc,
                "Ккал из ЭП, ккал/кг": enter_kcal,
                "Белок из ЭП, г/кг": enter_protein,
                "Жир из ЭП, г/кг": enter_fat,
                "Углеводы из ЭП, г/кг": enter_carb,
                "Лактоза из ЭП, г/кг": enter_lactose,
                **{k: v for k, v in res.items()},
            })

        # --- Excel ---
                # --- Excel ---
        def build_excel():
            rows = []

            def add(section, param="", value="", unit=""):
                rows.append({"Раздел": section,  "Значение": value, "Ед.": unit})

            add("Дата/время расчёта", "", datetime.now().strftime("%Y-%m-%d %H:%M"), "")
            add("Масса", "", m, "кг")
            add("")
            add("Энтеральное питание")
            add("Смесь", "", chosen_mix_name, "")
            add("Кратность кормлений", "", n_feeds, "р/сут")
            add("Объёмы кормлений, мл", "", ", ".join(f"{v:.0f}" for v in feed_volumes), "мл")
            add("Суточный объём ЭП", "", round(total_enter_ml, 1), "мл")
            add("Доза ЭП", "", round(dose_enter_per_kg, 1), "мл/кг/сут")
            add("Ккал ЭП", "", round(enter_kcal, 1), "ккал/кг/сут")
            add("Белок ЭП", "", round(enter_protein, 2), "г/кг/сут")
            add("Жир ЭП", "", round(enter_fat, 2), "г/кг/сут")
            add("Углеводы ЭП", "", round(enter_carb, 2), "г/кг/сут")
            add("Лактоза ЭП", "", round(enter_lactose, 2), "г/кг/сут")
            add("")
            add("Доза жидкости", "", dose_liq, "мл/кг/сут")
            add("Суточный объём жидкости (ЭП + ПП) на кг", "", round(res["daily_dose_liq"], 1), "мл")
            add("")
            add("Дозы для расчёта парентерального питания")
            add("Белок", "", dose_alb, "г/кг/сут")
            add("Жир", "", dose_fat, "г/кг/сут")
            add("Углеводная нагрузка", "", SpeedC, "мг/кг/мин")
            add("Калий", "", FPK, "ммоль/кг/сут")
            add("Кальций", "", FPCa, "мг/кг/сут")
            add("Натрий", "", DoseNa, "ммоль/кг/сут")
            add("Магний", "", DoseMg, "мг/кг/сут")
            add("Солувит", "", dose_sol_per_kg, "мл/кг/сут")
            add("Виталипид", "", dose_vit_per_kg, "мл/кг/сут")
            add("Р-р глюкозы C1", "", C1, "%")
            add("Р-р глюкозы C2", "", C2, "%")
            add("")
            add("Расчёт парентерального питания")
            add("Общий объём жидкости", "", round(res["daily_dose_liq"], 1), "мл")
            add("Объём ПП", "", round(daily_dose_parent_eat, 1), "мл")
            add("Объём ЭП (учитываемый)", "", round(v_enter_calc, 1), "мл")
            add("Общий объём глюкозы в инфузии", "", round(v_gluc, 1), "мл")
            add("")
            add("Инфузия глюкозы и электролитов")
            add("Концентрация общ. р-ра глюкозы", "", round(concentrate_gluc, 1), "%")
            if C2 == C1:
                add(f"Раствор {C1:.1f}%", "", round(v_gluc, 1), "мл")
            else:
                add(f"Глюкоза {C1}%", "", round(dose_gluc_C1, 1), "мл")
                add(f"Глюкоза {C2}%", "", round(dose_gluc_C2, 1), "мл")
            add("Аминовен Инфант 10%", "", round(res["daily_dose_amino_10"], 1), "мл")
            add("KCl 4%", "", round(res["K"], 1), "мл")
            add("NaCl 10%", "", round(res["Na"], 1), "мл")
            add("Ca gluconatis 10%", "", round(res["Ca"], 1), "мл")
            add("MgSO4 25%", "", round(res["Mg"], 1), "мл")
            add("Солувит", "", round(res["Sol"], 1), "мл")
            add("Скорость глюкозы и электролитов", "", round(sol_rate, 1), "мл / ч")
            add("")
            add("Инфузия липидов")
            add("Жировая эмульсия 20%", "", round(res["daily_dose_emulsion_fat_20"], 1), "мл")
            add("Виталипид", "", round(res["Vit"], 1), "мл")
            add("Скорость жиров", "", round(vit_rate, 1), "мл / ч")

            _total_kcal    = enter_kcal    + dose_alb * 4 + dose_fat * 9 + SpeedC * 1.44 * 3.4
            _total_protein = enter_protein + dose_alb
            _total_fat     = enter_fat     + dose_fat
            _total_carb    = enter_carb    + SpeedC * 1.44

            add("")
            add("Получаемые энергия и нутриенты")
            add("Ккал ЭП + ПП", "", round(_total_kcal, 1), "ккал/кг/сут")
            add("Белок ЭП + ПП", "", round(_total_protein, 2), "г/кг/сут")
            add("Жир ЭП + ПП", "", round(_total_fat, 2), "г/кг/сут")
            add("Углеводы ЭП + ПП", "", round(_total_carb, 2), "г/кг/сут")

            df = pd.DataFrame(rows)


            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Расчёт")
                ws = writer.sheets["Расчёт"]
                for col, width in zip("ABCD", [36, 34, 40, 14]):
                    ws.column_dimensions[col].width = width
                for cell in ws[1]:
                    cell.font = Font(bold=True)
            buffer.seek(0)
            return buffer

        excel_data = build_excel()
        st.download_button(
            label="📥 Скачать Excel",
            data=excel_data,
            file_name=f"ПП_{chosen_mix_name}_{datetime.now():%Y%m%d_%H%M}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )