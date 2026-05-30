"""
utils.py — DY Monitoring 공통 유틸리티
프로젝트 루트에 저장 후 각 페이지에서 import
"""
import streamlit as st
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가 (pages/ 서브폴더에서 import 가능하도록)
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ──────────────────────────────────────────────────────────────
# 스티키 상단 네비게이션
# ──────────────────────────────────────────────────────────────
_NAV_CSS = """
#dy-nav{
  position:fixed;top:0;left:0;right:0;height:46px;
  background:#111620;border-bottom:1px solid #222A3A;
  display:flex;align-items:center;padding:0 20px;gap:2px;
  z-index:999999;font-family:'Inter','Gowun Batang',sans-serif;
  box-shadow:0 2px 10px rgba(0,0,0,.5);
}
#dy-nav .logo{
  font-size:15px;font-weight:800;font-style:italic;
  color:#E4EAF6;margin-right:16px;flex-shrink:0;
  letter-spacing:-.02em;white-space:nowrap;
}
#dy-nav a{
  padding:5px 11px;border-radius:6px;
  font-size:12px;font-weight:500;
  color:#7A8CA4;text-decoration:none;
  white-space:nowrap;transition:all .15s;display:inline-block;
}
#dy-nav a:hover{background:#161C28;color:#E4EAF6;}
#dy-nav a.act{
  background:rgba(56,139,253,.18);color:#388BFD;font-weight:600;
}
/* 콘텐츠 영역 상단 여백 */
[data-testid="stMainBlockContainer"]{padding-top:54px!important;}
[data-testid="stHeader"]{display:none!important;}
"""

_NAV_JS = r"""
<script>
(function(){
var CSS = """ + f'`{_NAV_CSS}`' + r""";
var MAP = {
  '/':        ['🏠','홈'],
  '모니터링': ['📊','모니터링'],
  '투자자산': ['📈','투자자산'],
  '트렌딩':   ['🔥','트렌딩'],
  '리포트':   ['📑','리포트'],
  '일정':     ['📅','일정'],
  '스터디':   ['📚','스터디'],
  '이슈':     ['📰','이슈'],
};
var ORDER = ['홈','모니터링','투자자산','트렌딩','리포트','일정','스터디','이슈'];

function getLabel(href){
  try{
    var p = decodeURIComponent(new URL(href, location.href).pathname);
    if(p === '/' || p === '') return MAP['/'];
    for(var k in MAP){
      if(k !== '/' && p.indexOf(k) !== -1) return MAP[k];
    }
  }catch(e){}
  return null;
}

function build(){
  if(document.getElementById('dy-nav')) return;

  var sel = [
    'section[data-testid="stSidebar"] [data-testid="stPageLink"] a',
    '[data-testid="stSidebarNavItems"] a',
    'section[data-testid="stSidebar"] a[href]',
  ].join(',');

  var found = document.querySelectorAll(sel);
  if(!found.length){ setTimeout(build, 400); return; }

  var collected = {};
  found.forEach(function(el){
    var href = el.href || '';
    if(!href) return;
    var lbl = getLabel(href);
    if(lbl && !collected[lbl[1]]) collected[lbl[1]] = {href:href, lbl:lbl};
  });

  if(Object.keys(collected).length < 2){ setTimeout(build, 500); return; }

  var nav = document.createElement('nav');
  nav.id = 'dy-nav';

  var logo = document.createElement('div');
  logo.className = 'logo'; logo.textContent = '◈ DY';
  nav.appendChild(logo);

  var cur = decodeURIComponent(location.pathname);

  ORDER.forEach(function(name){
    var item = collected[name];
    if(!item) return;
    var a = document.createElement('a');
    a.href = item.href;
    a.textContent = item.lbl[0] + '\u00a0' + item.lbl[1];
    var p = decodeURIComponent(new URL(item.href, location.href).pathname);
    if((name==='홈' && (cur==='/'||cur==='')) ||
       (name!=='홈' && cur===p))
      a.classList.add('act');
    nav.appendChild(a);
  });

  var sty = document.createElement('style');
  sty.textContent = CSS;
  document.head.appendChild(sty);
  document.body.prepend(nav);
}

setTimeout(build, 150);
setTimeout(build, 600);
setTimeout(build, 1400);
new MutationObserver(function(){
  if(!document.getElementById('dy-nav')) build();
}).observe(document.body, {childList:true});
})();
</script>
"""

def render_sticky_nav():
    """
    스티키 상단 네비게이션 바 렌더링.
    각 페이지의 st.set_page_config() 바로 다음 줄에 호출.
    """
    # 1. JS 주입 (nav 빌더)
    st.markdown(_NAV_JS, unsafe_allow_html=True)

    # 2. 사이드바에 모든 페이지 링크 렌더링
    with st.sidebar:
        _pages = [
            ("Home.py",            "🏠  홈"),
            ("pages/1_모니터링.py", "📊  모니터링"),
            ("pages/3_투자자산.py", "📈  투자자산"),
            ("pages/7_트렌딩.py",   "🔥  트렌딩"),
            ("pages/8_리포트.py",   "📑  리포트"),
            ("pages/6_일정.py",     "📅  일정"),
            ("pages/4_스터디.py",   "📚  스터디"),
            ("pages/5_이슈.py",     "📰  이슈"),
        ]
        for _file, _label in _pages:
            try:
                st.page_link(_file, label=_label, use_container_width=True)
            except Exception:
                pass
        st.markdown(
            '<div style="height:1px;background:#222A3A;margin:8px 0 6px"></div>',
            unsafe_allow_html=True
        )

    # 3. 사이드바 펼치기 플로팅 버튼 (Streamlit 1.58 대응)
    # collapsedControl은 1.58에 존재하지 않음 → localStorage + DOM 방식
    _btn_css = (
        "position:fixed;top:14px;left:10px;z-index:999999;"
        "background:#0D1117;border:2px solid #388BFD;border-radius:10px;"
        "padding:9px 15px;cursor:pointer;font-size:14px;font-weight:700;"
        "color:#388BFD;box-shadow:0 2px 16px rgba(56,139,253,.5);"
        "display:none;align-items:center;gap:6px;font-family:sans-serif;user-select:none"
    )
    # JS: isCollapsed 판단 → localStorage false 설정 → 버튼 클릭 → transform 강제
    _btn_js = (
        "(function(){"
        + "function isCol(){"
        +   "var s=document.querySelector('section[data-testid=\"stSidebar\"]');"
        +   "return s?s.getBoundingClientRect().width<60:false;"
        + "}"
        + "function sync(){"
        +   "var b=document.getElementById('dymenu');"
        +   "if(b)b.style.display=isCol()?'flex':'none';"
        + "}"
        + "function expand(){"
        # 방법 1: localStorage stSidebarCollapsed-* = false
        +   "try{"
        +     "var ks=Object.keys(localStorage);"
        +     "for(var i=0;i<ks.length;i++){"
        +       "if(ks[i].indexOf('stSidebarCollapsed')===0){"
        +         "localStorage.setItem(ks[i],'false');"
        +         "window.dispatchEvent(new StorageEvent('storage',{key:ks[i],newValue:'false',storageArea:localStorage}));"
        +       "}"
        +     "}"
        +   "}catch(e){}"
        # 방법 2: stSidebarCollapseButton 버튼 클릭
        +   "try{"
        +     "var cb=document.querySelector('[data-testid=\"stSidebarCollapseButton\"] button');"
        +     "if(cb&&isCol())cb.click();"
        +   "}catch(e){}"
        # 방법 3: 직접 transform/margin 제거
        +   "setTimeout(function(){"
        +     "if(isCol()){"
        +       "var sb=document.querySelector('section[data-testid=\"stSidebar\"]');"
        +       "if(sb){sb.style.cssText+=';transform:none!important;margin-left:0!important;left:0!important;';}"
        +     "}"
        +   "},200);"
        + "}"
        + "window._dyExp=expand;"
        + "new MutationObserver(sync).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['style','class']});"
        + "setInterval(sync,500);"
        + "setTimeout(sync,800);setTimeout(sync,2000);"
        + "})()"
    )
    st.markdown(
        '<div id="dymenu" style="' + _btn_css + '" ' +
        'onclick="window._dyExp&&window._dyExp()">☰ 메뉴</div>' +
        '<script>' + _btn_js + '</script>',
        unsafe_allow_html=True
    )
