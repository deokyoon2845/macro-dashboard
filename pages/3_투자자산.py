"""3. 투자자산 — Phase1+2+3+수익률추이 통합"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime, date
import json, uuid

st.set_page_config(page_title="투자자산",page_icon="📈",layout="wide",
                   initial_sidebar_state="expanded")

BG="#0D1117"; CARD="#161B22"; C2="#1C2128"; BORD="#30363D"; G="#21262D"
TXT="#E6EDF3"; SUB="#8D96A0"; MUT="#6E7681"; PUR_HI="#1F6FEB"; PUR_DK="#58A6FF"
B5="#388BFD"; B6="#2F81F7"; B7="#1F6FEB"; B8="#1158C7"
UP="#3FB950"; DN="#F85149"

st.markdown(f"""<style>
html,body,[class*="css"]{{background-color:{BG}!important;color:{TXT}!important;
  font-family:'MaruBuri','Gowun Batang',serif!important;letter-spacing:.015em!important}}
.block-container{{padding:1.5rem 2rem 3rem!important;max-width:100%!important;background:transparent!important}}
[data-testid="stAppViewContainer"]{{background-color:{BG}!important}}
[data-testid="stSidebar"]{{background-color:{CARD}!important;border-right:1px solid {BORD}!important}}
#MainMenu,footer,header{{visibility:hidden}}
p,span,div,label,th,td{{color:{TXT}!important}}
.stButton>button{{background:{C2}!important;color:{TXT}!important;border:1px solid {BORD}!important;border-radius:8px!important}}
.stButton>button:hover{{border-color:{B5}!important;color:{B5}!important;background:{C2}!important}}
</style>""",unsafe_allow_html=True)

DATA = Path(__file__).parent.parent/"data"
PORT_FILE   = DATA/"portfolio.json"
PRICE_FILE  = DATA/"portfolio_prices.parquet"
MARKET_FILE = DATA/"market_prices.parquet"
NEWS_FILE   = DATA/"portfolio_news.json"
DISC_FILE   = DATA/"portfolio_disclosures.json"

SECTORS=["반도체","방산","증권·금융","우주항공","로봇·자동화","2차전지","바이오",
         "IT·소프트웨어","엔터·미디어","자동차","화학","철강·소재","건설","유틸리티","소비재","에너지","기타"]
MARKETS=["KOSPI","KOSDAQ","NYSE","NASDAQ","기타"]

def load_portfolio():
    if PORT_FILE.exists():
        with open(PORT_FILE,encoding="utf-8") as f: return json.load(f)
    return []

def save_portfolio(data):
    DATA.mkdir(exist_ok=True)
    with open(PORT_FILE,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)

@st.cache_data(ttl=600)
def load_prices():
    if PRICE_FILE.exists():
        df=pd.read_parquet(PRICE_FILE); df["date"]=pd.to_datetime(df["date"]); return df
    return pd.DataFrame()

@st.cache_data(ttl=600)
def load_market():
    if MARKET_FILE.exists():
        df=pd.read_parquet(MARKET_FILE); df["date"]=pd.to_datetime(df["date"]); return df
    return pd.DataFrame()

def load_news():
    if NEWS_FILE.exists():
        with open(NEWS_FILE,encoding="utf-8") as f: return json.load(f)
    return {"updated":"","stocks":{},"sectors":{}}

def load_disc():
    if DISC_FILE.exists():
        with open(DISC_FILE,encoding="utf-8") as f: return json.load(f)
    return {"updated":"","disclosures":{}}

def get_usdkrw(market_df):
    if market_df.empty or "indicator" not in market_df.columns: return 1380.0
    s=market_df[market_df["indicator"]=="USDKRW"].sort_values("date")
    return float(s.iloc[-1]["value"]) if not s.empty else 1380.0

def get_latest_price(ticker, prices):
    if prices.empty: return None, None
    sub=prices[prices["ticker"]==ticker].sort_values("date")
    if sub.empty: return None, None
    cur=float(sub.iloc[-1]["close"])
    prev=float(sub.iloc[-2]["close"]) if len(sub)>=2 else cur
    return cur, prev

def compute_position(item, prices, usdkrw):
    lots=item.get("lots",[]); ticker=item.get("ticker","")
    if not lots: return None
    total_qty=sum(l["qty"] for l in lots); total_cost=sum(l["qty"]*l["price"] for l in lots)
    avg=total_cost/total_qty if total_qty>0 else 0
    if total_qty<=0: return None
    cur, prev=get_latest_price(ticker,prices)
    is_usd=item.get("currency","KRW")=="USD"; fx=usdkrw if is_usd else 1
    if cur is None:
        return {"name":item["name"],"ticker":ticker,"sector":item.get("sector","기타"),
                "market":item.get("market","기타"),"currency":item.get("currency","KRW"),
                "qty":total_qty,"avg_cost":avg,"current":None,"price_date":None,
                "value_local":0,"value_krw":0,"cost_krw":total_cost*fx,
                "pnl_local":0,"pnl_krw":0,"pnl_pct":0,"daily_pnl_krw":0,"daily_pct":0,
                "id":item.get("id",""),"lots":lots,"notes":item.get("notes","")}
    value_l=cur*total_qty; pnl_l=(cur-avg)*total_qty; pnl_pct=(cur/avg-1)*100 if avg>0 else 0
    daily_pct=(cur/prev-1)*100 if prev>0 else 0; daily_pnl_l=(cur-prev)*total_qty if prev else 0
    return {"name":item["name"],"ticker":ticker,"sector":item.get("sector","기타"),
            "market":item.get("market","기타"),"currency":item.get("currency","KRW"),
            "qty":total_qty,"avg_cost":avg,"current":cur,"price_date":None,
            "value_local":value_l,"value_krw":value_l*fx,"cost_krw":total_cost*fx,
            "pnl_local":pnl_l,"pnl_krw":pnl_l*fx,"pnl_pct":pnl_pct,
            "daily_pnl_krw":daily_pnl_l*fx,"daily_pct":daily_pct,
            "id":item.get("id",""),"lots":lots,"notes":item.get("notes","")}

def compute_daily_portfolio(portfolio, prices, market_df):
    if prices.empty or not portfolio: return pd.DataFrame()
    all_dates=sorted(prices["date"].dropna().unique())
    fx_df=pd.DataFrame(); 
    if not market_df.empty and "indicator" in market_df.columns:
        fx_sub=market_df[market_df["indicator"]=="USDKRW"][["date","value"]].copy()
        if not fx_sub.empty: fx_df=fx_sub.rename(columns={"value":"fx"})
    rows=[]
    for d in all_dates:
        tv=0; tc=0; any_pos=False
        fx_now=1380.0
        if not fx_df.empty:
            fs=fx_df[fx_df["date"]<=d].sort_values("date")
            if not fs.empty: fx_now=float(fs.iloc[-1]["fx"])
        for it in portfolio:
            ticker=it.get("ticker",""); fxv=fx_now if it.get("currency","KRW")=="USD" else 1
            qty=0; cost=0
            for lot in it.get("lots",[]):
                if pd.Timestamp(lot["date"])<=d: qty+=lot["qty"]; cost+=lot["qty"]*lot["price"]
            if qty<=0: continue; any_pos=True
            ps=prices[(prices["ticker"]==ticker)&(prices["date"]<=d)].sort_values("date")
            if ps.empty: continue
            price=float(ps.iloc[-1]["close"])
            tv+=qty*price*fxv; tc+=cost*fxv
        if any_pos: rows.append({"date":d,"value":tv,"cost":tc,"pnl_pct":(tv/tc-1)*100 if tc>0 else 0})
    return pd.DataFrame(rows)

# ── 헤더 ─────────────────────────────────────────────────────
st.markdown(f"""
<div style="font-family:'MaruBuri',serif;font-size:28px;font-weight:700;font-style:italic;margin-bottom:4px">
  <span style="background:rgba(47,129,247,.28);padding:1px 8px;border-radius:5px">📈 투자자산 현황</span>
</div>
<div style="font-size:11px;color:{MUT};margin-bottom:1.5rem">
  평가손익 · 수익률 추이 · AI 뉴스 · DART 공시 (매일 KST 07:00 자동 업데이트)
</div>""",unsafe_allow_html=True)

portfolio=load_portfolio(); prices=load_prices(); market_df=load_market()
usdkrw=get_usdkrw(market_df)

# ══════════════════════════════════════════════════════════════
# 종목 관리
# ══════════════════════════════════════════════════════════════
mode=st.radio("작업",["📋 보유현황","➕ 신규 종목 등록","📝 매수 기록 추가","🗑️ 종목 관리"],
              horizontal=True,label_visibility="collapsed")

if mode=="➕ 신규 종목 등록":
    with st.form("new_form",clear_on_submit=True):
        c1,c2,c3=st.columns(3)
        with c1: n_name=st.text_input("종목명*",placeholder="삼성전자")
        with c2: n_ticker=st.text_input("yfinance 티커*",placeholder="005930.KS")
        with c3: n_currency=st.selectbox("통화*",["KRW","USD"])
        c4,c5,c6=st.columns(3)
        with c4: n_sector=st.selectbox("섹터",SECTORS)
        with c5: n_market=st.selectbox("시장",MARKETS)
        with c6: n_notes=st.text_input("메모","")
        st.caption("💡 티커: 코스피=005930.KS · 코스닥=247540.KQ · 미국=AAPL")
        st.markdown("**초기 매수 기록 (선택)**")
        c7,c8,c9=st.columns(3)
        with c7: n_lot_date=st.date_input("매수일",date.today())
        with c8: n_lot_qty=st.number_input("수량",min_value=0.0,step=1.0)
        with c9: n_lot_price=st.number_input("매수가",min_value=0.0,step=100.0)
        if st.form_submit_button("등록",type="primary"):
            if not n_name or not n_ticker: st.error("종목명과 티커는 필수입니다.")
            elif any(p.get("ticker")==n_ticker for p in portfolio): st.warning(f"이미 등록된 티커: {n_ticker}")
            else:
                new={"id":str(uuid.uuid4())[:8],"name":n_name,"ticker":n_ticker,
                     "sector":n_sector,"market":n_market,"currency":n_currency,
                     "notes":n_notes,"lots":[]}
                if n_lot_qty>0 and n_lot_price>0:
                    new["lots"].append({"date":str(n_lot_date),"qty":n_lot_qty,"price":n_lot_price})
                portfolio.append(new); save_portfolio(portfolio)
                st.cache_data.clear(); st.success(f"{n_name} 등록 완료!"); st.rerun()

elif mode=="📝 매수 기록 추가":
    if not portfolio: st.info("먼저 신규 종목을 등록해주세요.")
    else:
        with st.form("add_lot",clear_on_submit=True):
            opts={f"{p['name']} ({p['ticker']})":p["id"] for p in portfolio}
            sel=st.selectbox("종목 선택",list(opts.keys()))
            c1,c2,c3=st.columns(3)
            with c1: a_date=st.date_input("매수일",date.today())
            with c2: a_qty=st.number_input("수량*",min_value=0.0,step=1.0)
            with c3: a_price=st.number_input("매수가*",min_value=0.0,step=100.0)
            if st.form_submit_button("추가",type="primary"):
                if a_qty<=0 or a_price<=0: st.error("수량과 매수가는 0보다 커야 합니다.")
                else:
                    tid=opts[sel]
                    for p in portfolio:
                        if p.get("id")==tid:
                            p.setdefault("lots",[]).append({"date":str(a_date),"qty":a_qty,"price":a_price}); break
                    save_portfolio(portfolio); st.cache_data.clear()
                    st.success("매수 기록 추가됨"); st.rerun()

elif mode=="🗑️ 종목 관리":
    if not portfolio: st.info("등록된 종목이 없습니다.")
    else:
        for p in portfolio:
            lots=p.get("lots",[]); tqty=sum(l["qty"] for l in lots)
            with st.expander(f"📌 {p['name']} ({p['ticker']}) · {tqty:.0f}주"):
                if lots:
                    ldf=pd.DataFrame(lots); ldf.columns=["매수일","수량","매수가"]
                    st.dataframe(ldf,use_container_width=True,hide_index=True)
                if st.button("🗑️ 종목 삭제",key=f"del_{p['id']}"):
                    portfolio=[x for x in portfolio if x.get("id")!=p["id"]]
                    save_portfolio(portfolio); st.cache_data.clear(); st.rerun()

st.markdown(f'<div style="height:1px;background:{BORD};margin:1.5rem 0"></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 평가손익 집계
# ══════════════════════════════════════════════════════════════
positions=[compute_position(p,prices,usdkrw) for p in portfolio]
positions=[pos for pos in positions if pos]

if not positions:
    st.info("📊 보유 종목을 등록하고 매수 기록을 추가해주세요."); st.stop()

df=pd.DataFrame(positions)
df_p=df[df["current"].notna()]; df_np=df[~df["current"].notna()]

tv=df_p["value_krw"].sum(); tc=df_p["cost_krw"].sum()
tp=df_p["pnl_krw"].sum(); tpct=(tp/tc*100) if tc>0 else 0
td=df_p["daily_pnl_krw"].sum(); dpct=(td/(tv-td)*100) if (tv-td)>0 else 0

kpi_items=[("총 평가금액",f"{tv:,.0f}원",B5,""),
           ("총 평가손익",f"{tp:+,.0f}원",UP if tp>=0 else DN,f"{tpct:+.2f}%"),
           ("일간 변동",f"{td:+,.0f}원",UP if td>=0 else DN,f"{dpct:+.2f}%"),
           ("USD/KRW",f"{usdkrw:,.0f}",MUT,f"기준 환율")]
cols=st.columns(4)
for col,(lbl,val,clr,sub_) in zip(cols,kpi_items):
    with col:
        sh=f'<div style="font-size:10px;color:{clr};font-weight:600;margin-top:2px">{sub_}</div>' if sub_ else ""
        st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-left:3px solid {clr};border-radius:8px;padding:14px">
  <div style="font-size:10px;color:{MUT};text-transform:uppercase">{lbl}</div>
  <div style="font-size:20px;font-weight:700;color:{TXT};line-height:1.2;margin-top:3px;font-family:'JetBrains Mono',monospace">{val}</div>
  {sh}
</div>""",unsafe_allow_html=True)

if not df_np.empty:
    st.warning(f"⚠️ 가격 데이터 미수집: {', '.join(df_np['ticker'].tolist())} (내일 07:00 자동수집)")

st.markdown(f'<div style="height:1rem"></div>',unsafe_allow_html=True)

# ── 자산 배분 ─────────────────────────────────────────────────
def donut(df_,grp,title,palette):
    g=df_.groupby(grp)["value_krw"].sum().sort_values(ascending=False)
    if g.empty: return None
    fig=go.Figure(go.Pie(labels=g.index,values=g.values,hole=0.55,textinfo="label+percent",
        textfont=dict(size=10,family="MaruBuri"),
        marker=dict(colors=palette[:len(g)],line=dict(color=CARD,width=1.5)),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f}원 (%{percent})<extra></extra>"))
    fig.update_layout(title=dict(text=title,font=dict(size=11,color=SUB),x=0.01),
        paper_bgcolor=CARD,height=270,margin=dict(l=8,r=8,t=30,b=8),showlegend=False,
        annotations=[dict(text=f"{g.sum()/1e8:.1f}억",x=0.5,y=0.5,
            font=dict(size=14,color=TXT,family="JetBrains Mono"),showarrow=False)])
    return fig

PAL=[B5,B6,B7,B8,"#79C0FF","#58A6FF","#388BFD","#2F81F7","#1F6FEB"]
st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};margin-bottom:8px">자산 배분</div>',unsafe_allow_html=True)
cc1,cc2,cc3,cc4=st.columns(4)
for col,grp,title in [(cc1,"name","종목별"),(cc2,"sector","섹터별"),(cc3,"market","시장별"),(cc4,"currency","통화별")]:
    with col:
        pal=PAL if grp!="currency" else [B5,PUR_DK]
        fig=donut(df_p,grp,title,pal)
        if fig: st.plotly_chart(fig,use_container_width=True)

# ── 수익률 추이 ───────────────────────────────────────────────
hist_df=compute_daily_portfolio(portfolio,prices,market_df)

if not hist_df.empty and len(hist_df)>=2:
    st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};margin:1rem 0 8px">수익률 추이</div>',unsafe_allow_html=True)
    hc1,hc2=st.columns([2,1])
    with hc1:
        fig=make_subplots(specs=[[{"secondary_y":True}]])
        fig.add_trace(go.Scatter(x=hist_df["date"],y=hist_df["value"],name="평가금액 (좌)",
            line=dict(color=B5,width=2),fill="tozeroy",fillcolor="rgba(56,139,253,.08)",
            hovertemplate="<b>평가금액</b> %{y:,.0f}원<extra></extra>"),secondary_y=False)
        fig.add_trace(go.Scatter(x=hist_df["date"],y=hist_df["pnl_pct"],name="누적 수익률 (우)",
            line=dict(color=PUR_DK,width=1.5,dash="dot"),
            hovertemplate="<b>수익률</b> %{y:+.2f}%<extra></extra>"),secondary_y=True)
        fig.add_hline(y=0,line_dash="dot",line_color=MUT,line_width=1,secondary_y=True)
        fig.update_layout(paper_bgcolor=CARD,plot_bgcolor=CARD,height=300,
            font=dict(family="JetBrains Mono",size=10,color=MUT),margin=dict(l=8,r=8,t=28,b=8),
            title=dict(text="포트폴리오 추이",font=dict(size=11,color=SUB),x=0.01),
            legend=dict(orientation="h",y=1.08,x=0,font=dict(size=9),bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",xaxis=dict(showgrid=True,gridcolor=G,tickfont=dict(size=9,color=MUT)))
        fig.update_yaxes(secondary_y=False,gridcolor=G,tickformat=",.0f",ticksuffix="원",tickfont=dict(size=9,color=MUT))
        fig.update_yaxes(secondary_y=True,showgrid=False,tickformat="+.1f",ticksuffix="%",tickfont=dict(size=9,color=PUR_DK))
        st.plotly_chart(fig,use_container_width=True)
    with hc2:
        first_d=hist_df.iloc[0]["date"]
        first_v=hist_df.iloc[0]["value"]
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=hist_df["date"],y=hist_df["value"]/first_v*100,name="포트폴리오",
            line=dict(color=B5,width=2),hovertemplate="<b>포트폴리오</b> %{y:.2f}<extra></extra>"))
        if not market_df.empty and "indicator" in market_df.columns:
            for ind,nm,clr in [("KOSPI","KOSPI",PUR_DK),("SPX","S&P500",B8)]:
                sub=market_df[(market_df["indicator"]==ind)&(market_df["date"]>=first_d)].sort_values("date").copy()
                if not sub.empty:
                    sub["norm"]=sub["value"]/sub.iloc[0]["value"]*100
                    fig.add_trace(go.Scatter(x=sub["date"],y=sub["norm"],name=nm,
                        line=dict(color=clr,width=1.5,dash="dot"),hovertemplate=f"<b>{nm}</b> %{{y:.2f}}<extra></extra>"))
        fig.add_hline(y=100,line_dash="dot",line_color=MUT,line_width=1)
        fig.update_layout(paper_bgcolor=CARD,plot_bgcolor=CARD,height=300,
            font=dict(family="JetBrains Mono",size=10,color=MUT),margin=dict(l=8,r=8,t=28,b=8),
            title=dict(text="벤치마크 대비 (시작=100)",font=dict(size=11,color=SUB),x=0.01),
            legend=dict(orientation="h",y=1.08,x=0,font=dict(size=9),bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",xaxis=dict(showgrid=True,gridcolor=G,tickfont=dict(size=9,color=MUT)),
            yaxis=dict(showgrid=True,gridcolor=G,tickfont=dict(size=9,color=MUT)))
        st.plotly_chart(fig,use_container_width=True)
    # 월별 수익률
    if len(hist_df)>=30:
        hist_df["ym"]=hist_df["date"].dt.to_period("M").astype(str)
        monthly=hist_df.groupby("ym").agg(value=("value","last")).reset_index()
        if len(monthly)>=2:
            monthly["prev"]=monthly["value"].shift(1); monthly["ret"]=(monthly["value"]/monthly["prev"]-1)*100
            monthly=monthly.dropna(subset=["ret"])
            if not monthly.empty:
                clrs=[UP if r>=0 else DN for r in monthly["ret"]]
                fig=go.Figure(go.Bar(x=monthly["ym"],y=monthly["ret"],marker_color=clrs,
                    text=[f"{r:+.1f}%" for r in monthly["ret"]],textposition="outside",textfont=dict(size=9),
                    hovertemplate="<b>%{x}</b><br>%{y:+.2f}%<extra></extra>"))
                fig.add_hline(y=0,line_color=MUT,line_width=1)
                fig.update_layout(paper_bgcolor=CARD,plot_bgcolor=CARD,height=200,
                    title=dict(text="월별 수익률",font=dict(size=11,color=SUB),x=0.01),
                    font=dict(family="JetBrains Mono",size=10,color=MUT),margin=dict(l=8,r=8,t=28,b=8),
                    xaxis=dict(showgrid=False,tickfont=dict(size=9,color=MUT)),
                    yaxis=dict(showgrid=True,gridcolor=G,ticksuffix="%",tickfont=dict(size=9,color=MUT)))
                st.plotly_chart(fig,use_container_width=True)

# ── 일간 변동 TOP ─────────────────────────────────────────────
st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};margin:1rem 0 8px">일간 변동</div>',unsafe_allow_html=True)
dc1,dc2=st.columns(2)
with dc1:
    top_up=df_p.nlargest(5,"daily_pct")
    if not top_up.empty:
        fig=go.Figure(go.Bar(x=top_up["daily_pct"],y=top_up["name"],orientation="h",
            marker_color=UP,text=[f"+{p:.2f}%" for p in top_up["daily_pct"]],textposition="outside",
            hovertemplate="<b>%{y}</b><br>%{x:+.2f}%<extra></extra>"))
        fig.update_layout(paper_bgcolor=CARD,plot_bgcolor=CARD,height=230,
            title=dict(text="📈 일간 상승 TOP 5",font=dict(size=11,color=SUB),x=0.01),
            font=dict(family="JetBrains Mono",size=10,color=MUT),margin=dict(l=8,r=40,t=30,b=8),
            xaxis=dict(showgrid=True,gridcolor=G,tickformat="+.1f",ticksuffix="%",tickfont=dict(size=9,color=MUT)),
            yaxis=dict(autorange="reversed",tickfont=dict(size=10,color=TXT)))
        st.plotly_chart(fig,use_container_width=True)
with dc2:
    top_dn=df_p.nsmallest(5,"daily_pct")
    if not top_dn.empty and (top_dn["daily_pct"]<0).any():
        fig=go.Figure(go.Bar(x=top_dn["daily_pct"],y=top_dn["name"],orientation="h",
            marker_color=DN,text=[f"{p:.2f}%" for p in top_dn["daily_pct"]],textposition="outside",
            hovertemplate="<b>%{y}</b><br>%{x:+.2f}%<extra></extra>"))
        fig.update_layout(paper_bgcolor=CARD,plot_bgcolor=CARD,height=230,
            title=dict(text="📉 일간 하락 TOP 5",font=dict(size=11,color=SUB),x=0.01),
            font=dict(family="JetBrains Mono",size=10,color=MUT),margin=dict(l=8,r=40,t=30,b=8),
            xaxis=dict(showgrid=True,gridcolor=G,tickformat="+.1f",ticksuffix="%",tickfont=dict(size=9,color=MUT)),
            yaxis=dict(autorange="reversed",tickfont=dict(size=10,color=TXT)))
        st.plotly_chart(fig,use_container_width=True)

# ── 보유 종목 상세 표 ──────────────────────────────────────────
st.markdown(f'<div style="font-size:14px;font-weight:600;color:{SUB};margin:1rem 0 8px">보유 종목 상세</div>',unsafe_allow_html=True)
df_sorted=df.sort_values("value_krw",ascending=False)

def fmt_row(r):
    pclr=UP if r["pnl_krw"]>=0 else DN; dclr=UP if r["daily_pct"]>=0 else DN
    sp="▲" if r["pnl_pct"]>=0 else "▼"; sd="▲" if r["daily_pct"]>=0 else "▼"
    wt=(r["value_krw"]/tv*100) if tv>0 else 0
    cv=f"{r['current']:,.2f}" if r["current"] else "—"
    return f"""<tr style="border-bottom:1px solid {BORD}">
  <td style="padding:.6rem .8rem"><div style="font-size:12px;font-weight:600;color:{TXT}">{r['name']}</div>
    <div style="font-size:9px;color:{MUT};font-family:'JetBrains Mono',monospace">{r['ticker']}</div></td>
  <td style="padding:.6rem .8rem;font-size:10px;color:{MUT}">{r['sector']}<br><span style="font-size:9px">{r['market']}</span></td>
  <td style="padding:.6rem .8rem;text-align:right;font-family:'JetBrains Mono',monospace;font-size:11px;color:{TXT}">{r['qty']:,.0f}</td>
  <td style="padding:.6rem .8rem;text-align:right;font-family:'JetBrains Mono',monospace;font-size:11px;color:{TXT}">{r['avg_cost']:,.2f}</td>
  <td style="padding:.6rem .8rem;text-align:right;font-family:'JetBrains Mono',monospace;font-size:11px;color:{TXT}">{cv}<br>
    <span style="font-size:9px;color:{dclr};font-weight:600">{sd}{abs(r['daily_pct']):.2f}%</span></td>
  <td style="padding:.6rem .8rem;text-align:right;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;color:{TXT}">{r['value_krw']:,.0f}원<br>
    <span style="font-size:9px;color:{MUT}">({wt:.1f}%)</span></td>
  <td style="padding:.6rem .8rem;text-align:right;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;color:{pclr}">{r['pnl_krw']:+,.0f}원<br>
    <span style="font-size:9px">{sp}{abs(r['pnl_pct']):.2f}%</span></td>
</tr>"""

rows_html="".join(fmt_row(r) for _,r in df_sorted.iterrows())
TH=f"padding:.5rem .8rem;text-align:left;font-size:9px;color:{MUT};font-weight:500;border-bottom:1px solid {BORD}"
st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;overflow:hidden">
<table style="width:100%;border-collapse:collapse">
  <thead><tr style="background:{C2}">
    <th style="{TH}">종목</th><th style="{TH}">섹터</th><th style="{TH};text-align:right">수량</th>
    <th style="{TH};text-align:right">평균단가</th><th style="{TH};text-align:right">현재가·일간</th>
    <th style="{TH};text-align:right">평가금액(비중)</th><th style="{TH};text-align:right">평가손익</th>
  </tr></thead><tbody>{rows_html}</tbody>
</table></div>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 관련 뉴스 + DART 공시
# ══════════════════════════════════════════════════════════════
news_data=load_news(); disc_data=load_disc()

def fmt_iso(s):
    try: return datetime.fromisoformat(s).strftime("%Y-%m-%d %H:%M")
    except: return (s or "")[:16]

st.markdown(f"""
<div style="height:2rem"></div>
<div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:8px">
  <span style="font-size:14px;font-weight:600;color:{SUB};font-family:'MaruBuri',serif">📰 뉴스 · 공시</span>
  <span style="font-size:9px;color:{MUT};font-family:'JetBrains Mono',monospace">
    뉴스 {fmt_iso(news_data.get('analyzed_at',''))} · 공시 {fmt_iso(disc_data.get('updated',''))}
  </span>
</div>""",unsafe_allow_html=True)

def sentiment_chip(score):
    if score is None: return ""
    if score>=7:   lbl,fg,bg="호재",B5,"rgba(56,139,253,.2)"
    elif score<=3: lbl,fg,bg="악재",B8,"rgba(17,88,199,.2)"
    else:          lbl,fg,bg="중립",MUT,C2
    return (f'<span style="background:{bg};color:{fg};padding:2px 7px;border-radius:9px;'
            f'font-size:9px;font-weight:600;font-family:JetBrains Mono,monospace;border:1px solid {fg}30">{lbl} {score}</span>')

def news_card(news, accent=B5):
    title=news.get("title",""); url=news.get("url","#")
    body=news.get("ai_summary") or news.get("summary","")
    source=(news.get("source") or "")[:30]; pub=news.get("pub_date","")
    score=news.get("score"); tags=news.get("tags",[])
    try:
        dt_s=pub.replace("Z","+00:00").split("+")[0] if "+" in pub else pub
        ds=datetime.fromisoformat(dt_s).strftime("%m-%d %H:%M")
    except: ds=pub[:10] if pub else ""
    badge=sentiment_chip(score)
    tag_html=('<div style="margin-top:5px;display:flex;gap:3px;flex-wrap:wrap">'+"".join(
        f'<span style="background:{C2};color:{SUB};padding:1px 6px;border-radius:5px;font-size:8px;font-family:JetBrains Mono,monospace">#{t}</span>'
        for t in tags[:2])+"</div>") if tags else ""
    ms="font-size:10.5px;color:"+TXT+";font-weight:500;line-height:1.5" if news.get("ai_summary") else "font-size:10px;color:"+SUB+";line-height:1.5"
    return f"""<a href="{url}" target="_blank" rel="noopener" style="text-decoration:none;color:inherit">
<div style="background:{CARD};border:1px solid {BORD};border-top:2px solid {accent};border-radius:8px;padding:12px 14px;margin-bottom:10px;height:200px;display:flex;flex-direction:column">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px;margin-bottom:6px">
    <div style="font-size:12px;font-weight:600;color:{TXT};line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;flex:1">{title}</div>
    {badge}
  </div>
  <div style="{ms};flex:1;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical">{body}</div>
  {tag_html}
  <div style="display:flex;justify-content:space-between;margin-top:6px;padding-top:6px;border-top:1px solid {BORD};font-size:9px;color:{MUT};font-family:JetBrains Mono,monospace">
    <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:60%">{source}</span>
    <span>{ds}</span>
  </div>
</div></a>"""

def disc_card(d):
    title=d.get("title",""); url=d.get("url","#"); filer=d.get("filer","")
    dt=d.get("date","")
    if len(dt)==8: dt=f"{dt[4:6]}-{dt[6:8]}"
    return f"""<a href="{url}" target="_blank" rel="noopener" style="text-decoration:none;color:inherit">
<div style="background:{CARD};border:1px solid {BORD};border-top:2px solid {B7};border-radius:8px;padding:12px 14px;margin-bottom:10px;min-height:90px;display:flex;flex-direction:column;justify-content:space-between">
  <div style="font-size:12px;font-weight:600;color:{TXT};line-height:1.45;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical">{title}</div>
  <div style="display:flex;justify-content:space-between;margin-top:8px;padding-top:6px;border-top:1px solid {BORD};font-size:9px;color:{MUT};font-family:JetBrains Mono,monospace">
    <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:65%">{filer}</span>
    <span>{dt}</span>
  </div>
</div></a>"""

tab_stock,tab_sector,tab_dart=st.tabs(["📌 종목 뉴스","🏭 산업 뉴스","📑 공시 (DART)"])

with tab_stock:
    stocks=news_data.get("stocks",{})
    ordered=[(r["name"],stocks[r["name"]]) for _,r in df_sorted.iterrows() if r["name"] in stocks and stocks[r["name"]]]
    if not ordered: st.info("종목 뉴스 미수집. 내일 KST 07:00 자동수집됩니다.")
    else:
        for name,articles in ordered:
            scores=[a.get("score") for a in articles if a.get("score") is not None]
            avg_s=sum(scores)/len(scores) if scores else None
            tone_html=""
            if avg_s is not None:
                tc=B5 if avg_s>=6.5 else (B8 if avg_s<=3.5 else MUT); tbg="rgba(56,139,253,.2)" if avg_s>=6.5 else ("rgba(17,88,199,.2)" if avg_s<=3.5 else C2)
                tone_html=f'<span style="background:{tbg};color:{tc};padding:2px 8px;border-radius:9px;font-size:9px;font-weight:600;margin-left:8px;font-family:JetBrains Mono,monospace">평균 {avg_s:.1f}</span>'
            st.markdown(f'<div style="font-size:13px;font-weight:700;color:{TXT};margin:1rem 0 .6rem;padding:6px 12px;background:{C2};border-left:3px solid {B5};border-radius:4px;font-family:\'MaruBuri\',serif;display:flex;align-items:center">{name}{tone_html}</div>',unsafe_allow_html=True)
            cols=st.columns(3)
            for col,news in zip(cols,articles[:3]):
                with col: st.markdown(news_card(news,accent=B5),unsafe_allow_html=True)

with tab_sector:
    sectors=news_data.get("sectors",{})
    sec_w=df_p.groupby("sector")["value_krw"].sum().sort_values(ascending=False)
    ordered_s=[s for s in sec_w.index if s in sectors and sectors[s]]
    if not ordered_s: st.info("산업 뉴스 미수집. 내일 KST 07:00 자동수집됩니다.")
    else:
        for sec in ordered_s:
            st.markdown(f'<div style="font-size:13px;font-weight:700;color:{TXT};margin:1rem 0 .6rem;padding:6px 12px;background:{C2};border-left:3px solid {PUR_DK};border-radius:4px">{sec}</div>',unsafe_allow_html=True)
            cols=st.columns(3)
            for col,news in zip(cols,sectors[sec][:3]):
                with col: st.markdown(news_card(news,accent=PUR_DK),unsafe_allow_html=True)

with tab_dart:
    discs=disc_data.get("disclosures",{})
    if not discs: st.info("공시 미수집. DART_API_KEY를 GitHub Secrets에 등록해주세요.")
    else:
        ordered_d=[(r["name"],discs[r["name"]]) for _,r in df_sorted.iterrows() if r["name"] in discs and discs[r["name"]]]
        if not ordered_d: st.info("최근 14일간 주요 공시 없음.")
        else:
            for name,items_ in ordered_d:
                st.markdown(f'<div style="font-size:13px;font-weight:700;color:{TXT};margin:1rem 0 .6rem;padding:6px 12px;background:{C2};border-left:3px solid {B7};border-radius:4px">{name} <span style="font-size:10px;color:{MUT};font-weight:400">{len(items_)}건</span></div>',unsafe_allow_html=True)
                cols=st.columns(3)
                for i,d_ in enumerate(items_[:6]):
                    with cols[i%3]: st.markdown(disc_card(d_),unsafe_allow_html=True)

st.markdown(f"""
<div style="margin-top:2rem;padding:10px 14px;background:{C2};border:1px solid {BORD};
  border-radius:8px;font-size:10px;color:{MUT};font-family:'JetBrains Mono',monospace">
  📅 가격 최종 업데이트: {prices["date"].max().strftime("%Y-%m-%d") if not prices.empty else "—"}  ·  USD/KRW: {usdkrw:,.0f}
</div>
""",unsafe_allow_html=True)
