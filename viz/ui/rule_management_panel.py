import streamlit as st

from core.rule_management import (
    add_rule,
    rename_rule,
    delete_rule,
)

# Render controls for adding, renaming, and deleting rules.
def render_rule_management_panel(rule_names, prec_df, eps):
    with st.expander("Manage rules"):
        st.subheader("Add rule")

        new_rule_name = st.text_input(
            "New rule name",
            key="manage_new_rule_name",
        )

        if st.button("Add rule", key="manage_add_rule"):
            try:
                rule_names, eq_classes, eps = add_rule(
                    rule_names,
                    st.session_state.eq_classes,
                    eps,
                    new_rule_name,
                )

                st.session_state.eq_classes = eq_classes
                sync_rule_session_state(rule_names, eps)

                st.rerun()
            except Exception as e:
                st.warning(str(e))

        st.divider()

        st.subheader("Rename rule")

        old_name = st.selectbox(
            "Rule to rename",
            rule_names,
            key="manage_rename_old",
        )

        new_name = st.text_input(
            "New name",
            key="manage_rename_new",
        )

        if st.button("Rename rule", key="manage_rename_rule"):
            try:
                rule_names, eq_classes, prec_df = rename_rule(
                    rule_names,
                    st.session_state.eq_classes,
                    prec_df,
                    old_name,
                    new_name,
                )

                st.session_state.eq_classes = eq_classes
                st.session_state.prec_df = prec_df

                sync_rule_session_state(rule_names,st.session_state.eps_values,)

                st.rerun()
            except Exception as e:
                st.warning(str(e))

        st.divider()

        st.subheader("Delete rule")

        rule_to_delete = st.selectbox(
            "Rule to delete",
            rule_names,
            key="manage_delete_rule_select",
        )

        if st.button("Delete rule", key="manage_delete_rule"):
            try:
                rule_names, eq_classes, prec_df, eps = delete_rule(
                    rule_names,
                    st.session_state.eq_classes,
                    prec_df,
                    eps,
                    rule_to_delete,
                )

                st.session_state.eq_classes = eq_classes
                st.session_state.prec_df = prec_df

                sync_rule_session_state(rule_names, eps)

                st.rerun()

            except Exception as e:
                st.warning(str(e))


# Keep Streamlit session state consistent whenever the rule list changes.
def sync_rule_session_state(rule_names, eps):
    st.session_state.rule_names_csv = ",".join(rule_names)
    st.session_state.eps_values = eps
    st.session_state.k = len(rule_names)

    for i, val in enumerate(eps):
        st.session_state[f"eps_{i}"] = float(val)

    # Remove old epsilon widgets after deleting rules.
    j = len(eps)
    while f"eps_{j}" in st.session_state:
        st.session_state.pop(f"eps_{j}", None)
        j += 1