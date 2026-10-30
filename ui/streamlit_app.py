import os

import httpx
import streamlit as st

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="AI Travel Planner", page_icon="🧭")
st.title("AI Travel Planner")
st.caption("Costs are model estimates. Check prices before you book.")

with st.form("trip"):
    destination = st.text_input("Destination", value="Goa")
    col1, col2 = st.columns(2)
    days = col1.number_input("Days", min_value=1, max_value=14, value=3)
    travellers = col2.number_input("Travellers", min_value=1, max_value=10, value=2)
    budget = st.number_input("Total budget (INR)", min_value=1000, value=30000, step=1000)
    interests = st.text_input("Interests, separated by commas", value="beaches, food")
    submitted = st.form_submit_button("Plan my trip")

if submitted:
    payload = {
        "destination": destination,
        "days": int(days),
        "travellers": int(travellers),
        "budget_inr": int(budget),
        "interests": [item.strip() for item in interests.split(",") if item.strip()],
    }
    try:
        with st.spinner("Planning your trip..."):
            response = httpx.post(f"{API_URL}/plan", json=payload, timeout=180)
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        st.error(f"The planner could not finish: {error.response.text}")
    except httpx.HTTPError as error:
        st.error(f"Could not reach the API at {API_URL}: {error}")
    else:
        result = response.json()
        cost = result["cost"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Estimated total", f"₹{cost['total_inr']:,}")
        col2.metric("Budget", f"₹{cost['budget_inr']:,}")
        col3.metric("Remaining", f"₹{cost['remaining_inr']:,}")
        if not cost["within_budget"]:
            st.warning("This plan is still over budget. Try a higher budget or fewer days.")

        for day in result["itinerary"]["days"]:
            with st.expander(f"Day {day['day']}: {day['title']}", expanded=True):
                for activity in day["activities"]:
                    st.markdown(
                        f"**{activity['time_of_day'].title()}: {activity['name']}** (₹{activity['cost_inr']:,})  \n"
                        f"{activity['description']}"
                    )
                st.caption(
                    f"Stay ₹{day['stay_cost_inr']:,} | Food ₹{day['food_cost_inr']:,} | "
                    f"Local transport ₹{day['local_transport_cost_inr']:,}"
                )

        if result["itinerary"]["tips"]:
            st.subheader("Tips")
            for tip in result["itinerary"]["tips"]:
                st.markdown(f"- {tip}")
        if result["sources"]:
            st.caption("Notes used: " + ", ".join(result["sources"]))
