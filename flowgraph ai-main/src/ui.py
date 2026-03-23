import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import streamlit as st
from src.graph import app


def main():
    st.title("AI Application")

    user_input = st.text_area("Please enter your text:", height=200)

    if st.button("Run"):
        if user_input:
            response = app(user_input)
            st.subheader("Result:")
            st.write(response)
        else:
            st.warning("Please enter a text.")


if __name__ == "__main__":
    main()
