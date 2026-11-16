# Auth-independent pilot only

N=3 per matchup, 12 games total, 16.98 s wall time. No Haiku calls succeeded or were substituted. The 3×3 completion criterion remains blocked by CLI authentication.

| Offense | Defense | Wins | Turnovers | Mistake rate | Abstract gap |
|---|---|---:|---:|---:|---:|
| Calculator | Calculator | 0/3 | 3/3 | .145 | +.216 |
| Calculator | Scripted | 0/3 | 3/3 | .150 | +.216 |
| Scripted | Calculator | 2/3 | 1/3 | .078 | -.450 |
| Scripted | Scripted | 0/3 | 0/3 | .133 | +.216 |

Conditional score turns: Scripted vs Calculator mean 9, bootstrap 95% CI [7,11]; other matchups have no scores. Rate and gap confidence intervals are in summary.json. No performance conclusion is supported by this small pilot and two representatives per abstract state/action.

8 unit tests passed. Model construction 2.568 s; solve plus support attractors 0.178 s; 31,106 total abstract states. Exact finite-horizon Bellman termination after 30 backups. Bounded positive region counts [15,550 offense-side, 15,547 defense-side]; bounded almost-sure counts [0,0].

Four figures, each PNG/PDF: win_rate, turnover_rate, mistake_rate, abstraction_gap. Real-game videos: demo_Calculator.mp4 and demo_Scripted.mp4. video_checked.png was extracted from Calculator MP4 with ffmpeg and opened: field, shaded endzone, both teams, disc and title render correctly. Source frame PNGs are also supplied.

Placeholder throw curve and all sampling/metric restrictions are documented in ../README.md. proposal.tex was not edited.
