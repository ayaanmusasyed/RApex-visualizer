# function to get the name of a node from its id 
def id_to_label(state_id: int) -> str:
    name_to_id = st.session_state.get("name_to_id", {})
    rev = {v: k for k, v in name_to_id.items()}
    return rev.get(state_id, str(state_id))