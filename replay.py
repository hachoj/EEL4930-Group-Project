"""Landscape pitch and synchronized concrete/abstract replays."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch
from matplotlib.animation import FuncAnimation, FFMpegWriter

def pitch(ax,h,g,previous=None,alpha=1,show_marks=True,abstract=False):
    ax.clear();ax.set(xlim=(-1,21),ylim=(-1,11),aspect='equal');ax.set_facecolor('#287a41');ax.set_xticks([]);ax.set_yticks([])
    for y in range(20):ax.add_patch(Rectangle((y-.5,-.5),1,10,color='white',alpha=.035 if y%2 else .075))
    for start in (-.5,16.5):
        ax.add_patch(Rectangle((start,-.5),3,10,color='#133d2b',alpha=.35));ax.text(start+1.5,4.5,'ENDZONE',rotation=90,ha='center',va='center',color='white',alpha=.5)
    ax.add_patch(Rectangle((-.5,-.5),20,10,fill=False,edgecolor='white',lw=2))
    for y in (2.5,16.5):ax.plot([y,y],[-.5,9.5],color='white',lw=1.5)
    ax.plot([6.5],[4.5],marker='x',color='white');ax.text(6.5,3.8,'brick',color='white',ha='center',fontsize=7)
    o=np.array(h['o'],float);d=np.array(h['d'],float)
    if previous is not None:
        o=alpha*o+(1-alpha)*np.array(previous['o']);d=alpha*d+(1-alpha)*np.array(previous['d'])
    marks=h.get('marks',[0,1,2])
    if abstract:
        from ultimate import key,zone
        k=key(h['o'],h['d']);edges=[-.5,4.5,9.5,14.5,16.5,19.5]
        for depth in range(5):
            for lane in range(3):
                lo=[-.5,3.5,6.5][lane];hi=[3.5,6.5,9.5][lane]
                ax.add_patch(Rectangle((edges[depth],lo),edges[depth+1]-edges[depth],hi-lo,fill=False,edgecolor='white',alpha=.5))
                ax.text(edges[depth]+.15,lo+.15,f'Z{3*depth+lane}',color='white',fontsize=6)
        for j,z in enumerate(k[:3]):
            dep,lane=divmod(z,3);x=(edges[dep]+edges[dep+1])/2;y=[1.5,5,8][lane]+(j-1)*.5
            color=['#efbb53','#d68af0','#9bdfba'][k[j+2]] if j else '#64c8ff'
            ax.text(x,y,['A ●','B','C'][j],ha='center',color=color,weight='bold',bbox=dict(facecolor='#102b35',alpha=.85,boxstyle='round'))
        ax.text(.01,.01,'A ● holder    Receiver coverage: gold front · purple behind · mint far',transform=ax.transAxes,color='white',fontsize=8)
        ax.set_title('Calculator view: 3 lanes × 5 depths (endzone separated)',color='#173628');return
    if show_marks:
        for j,m in enumerate(marks):ax.plot([d[j,1],o[m,1]],[d[j,0],o[m,0]],'--',color='white',alpha=.4,lw=1)
    for team,labels,color,marker in ((o,['A','B','C'],'#247de0','s'),(d,['D1','D2','D3'],'#e45a43','h')):
        ax.scatter(team[:,1],team[:,0],s=240,c=color,marker=marker,edgecolor='white',lw=1.2,zorder=5)
        for pos,label in zip(team,labels):ax.text(pos[1],pos[0],label,ha='center',va='center',color='white',fontsize=8,weight='bold',zorder=6)
    disc=h['thrower'];ax.add_patch(Circle((disc[1]+.17,disc[0]-.17),.17,color='black',alpha=.4,zorder=7));ax.add_patch(Circle((disc[1],disc[0]),.15,color='white',ec='#bbb',zorder=8))
    if h['receiver']:
        a=h['thrower'];b=h['receiver'];ax.add_patch(FancyArrowPatch((a[1],a[0]),(b[1],b[0]),connectionstyle='arc3,rad=.25',arrowstyle='->',mutation_scale=16,color='#ffe569',lw=2,zorder=9))
        ax.text((a[1]+b[1])/2,(a[0]+b[0])/2+1,f"p={h['p']:.3f} · {h.get('throw_result','').upper()}",color='white',ha='center',bbox=dict(facecolor='#182c29',alpha=.9),zorder=10)
    ax.set_title(f"BLUE {g['offense']} offense   |   RED {g['defense']} defense   |   Turn {h['turn']}   |   {h.get('_outcome','PLAYING')}",fontsize=10,color='#173628',weight='bold')

def render_replays(games,out,show_marks=True):
    for name in sorted({g['offense'] for g in games}):
        g=next(g for g in games if g['offense']==name);hist=g['history'];fig,axes=plt.subplots(2,1,figsize=(12,12));fig.set_facecolor('#e7eee7')
        frames=len(hist)*4+16
        def frame(i):
            idx=min(i//4,len(hist)-1);h=dict(hist[idx]);h['_outcome']=g['outcome'].upper() if i>=len(hist)*4-1 else 'PLAYING'
            prev=hist[idx-1] if idx else None
            # Last catch swaps labels before the next move: preserve player identity in interpolation.
            if prev and prev.get('throw_result')=='caught' and prev['receiver'] in prev['o']:
                prev=dict(prev);prev['o']=[p[:] for p in prev['o']];r=prev['o'].index(prev['receiver']);prev['o'][0],prev['o'][r]=prev['o'][r],prev['o'][0]
            pitch(axes[0],h,g,prev,1 if i>=len(hist)*4 else min(1,(i%4+1)/4),show_marks)
            pitch(axes[1],h,g,abstract=True)
            fig.tight_layout()
        anim=FuncAnimation(fig,frame,frames=frames,interval=125)
        anim.save(out/f'demo_{name}.mp4',writer=FFMpegWriter(fps=8,codec='libx264',extra_args=['-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1']))
        idx=next((i for i,h in enumerate(hist) if h['receiver']),0);frame(idx*4+3)
        fig.savefig(out/f'demo_{name}_frame.png',dpi=140)
        if name=='Calculator':
            comparison,panels=plt.subplots(1,2,figsize=(18,6))
            pitch(panels[0],hist[idx],g,show_marks=show_marks)
            pitch(panels[1],hist[idx],g,abstract=True)
            comparison.tight_layout()
            for ext in ('png','pdf'):comparison.savefig(out/f'calculator_view.{ext}',dpi=180)
            plt.close(comparison)
        plt.close(fig)
