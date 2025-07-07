import streamlit as st
import requests 

st.title("📰 News Fact-Checker App")
st.markdown(
    "<p style='font-size: 12px; color: grey;'>By Abhiraj, Suryansh, Abhishek, Nikunj</p>",
    unsafe_allow_html=True
)

st.write("This app can fetch latest news headlines and also fact-check any headlines.")

news_api_key = "6c6642268bd8474fbf2061cf9c46ec03"
fact_check_api_key = "AIzaSyA30vwHAA-pwLqRgxUMhpFC62Q5m5Zwy3w"

st.header("1. Checkout Latest News Headlines")

articles = []
if st.button("Fetch News Headlines"):
    news_url = (
        f"https://newsapi.org/v2/top-headlines?"
        f"country=us&apiKey={news_api_key}"
    )
    response = requests.get(news_url)
    data = response.json()
    articles = data.get("articles", [])

if articles:
    st.success("Latest News Headlines:")
    for i, article in enumerate(articles[:5], start=1):
        st.subheader(f"News {i}: {article['title']}")
        if article.get("url"):
            st.markdown(f"[→ Read Full News]({article['url']})", unsafe_allow_html=True)

st.header("2. Fact-Check a News Headline")

headline = st.text_input("Enter the news headline you want to fact-check:")
claims = [] 

if st.button("Check Fact"):
    if not headline.strip():
        st.warning("Please enter a valid news headline.")
    else:
        fact_check_url = (
            "https://factchecktools.googleapis.com/v1alpha1/claims:search"
            f"?query={requests.utils.quote(headline)}&key=AIzaSyA30vwHAA-pwLqRgxUMhpFC62Q5m5Zwy3w"
        )
        result = requests.get(fact_check_url).json()
        claims = result.get("claims", [])

if claims:
    st.success("Fact-Check Results Found:")
    for claim in claims[:3]:
        st.write("Claimed News:", claim.get("text", "N/A"))
        st.write(
            "Rating:",
            claim.get("claimReview", [{}])[0].get("textualRating", "N/A")
        )
        st.write(
            "Source:",
            claim.get("claimReview", [{}])[0].get("publisher", {}).get("name", "N/A")
        )
        url = claim.get("claimReview", [{}])[0].get("url")
        if url:
            st.markdown(f"[→ View Fact-Check Source]({url})", unsafe_allow_html=True)
        st.write("---")
elif headline: 
    st.info(
        "No fact-check result found for this headline. "
        "New or breaking news may not be fact-checked immediately."
    )
