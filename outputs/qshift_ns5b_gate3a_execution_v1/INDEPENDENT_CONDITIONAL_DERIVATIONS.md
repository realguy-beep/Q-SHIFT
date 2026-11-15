# Independent Conditional Derivations

No existing source was executed. These hand derivations do not validate the Q-SHIFT support map.

## C2 parity characters

For a fixed detector subset `A`, one categorical site outcome with support `S` contributes `(-1)^|A∩S|`. Averaging over mutually exclusive outcomes gives `g_j(A)=Σ_o p[j,o](-1)^|A∩S[j,o]|`. Independence across sites makes the expectation of the product equal `χ(A)=Π_j g_j(A)`. From `(-1)^D=1−2D`, `E[D_i]=(1−χ_i)/2`. Also `(-1)^(D_i+D_k)=1−2D_i−2D_k+4D_iD_k`, hence `E[D_iD_k]=(1−χ_i−χ_k+χ_ik)/4`. The Q-SHIFT application still requires C1.

## C4 edge inversion

For independent Bernoulli `A,B,E` with rates `a,b,p`, set `D_i=A⊕E`, `D_j=B⊕E`, `α=1−2a`, `β=1−2b`. Then `χ_i=α(1−2p)`, `χ_j=β(1−2p)`, `χ_ij=αβ`. The pair mean identity yields `χ_ij=1−2(m_i+m_j)+4q`, and covariance is `q−m_im_j=(χ_ij−χ_iχ_j)/4=χ_ij p(1−p)`. For `χ_ij≠0`, let `r=(q−m_im_j)/χ_ij`; real solutions require `0≤r≤1/4`, and `p=(1−√(1−4r))/2` on the lower branch. Without a branch constraint this identifies `min(p,1−p)`, not `p` globally.

## C8 one-step factor

For `m0>0`, `0≤λ≤1`, `X∈[0,1]`, `L=1+λ(X/m0−1)`. Its minimum is at `X=0`, so `L≥1−λ≥0`. If `E[X|F]≤m0`, then `E[L|F]=1+λ(E[X|F]/m0−1)≤1`. Under adaptedness/integrability this gives the nonnegative supermartingale. A random `λ` requires predictability and the same bounds; the proof does not cover a non-predictable data-selected λ.

## C9 mixture

`w_s=1/[s(s+1)]=1/s−1/(s+1)`. Thus `Σ_{s≤t}w_s=1−1/(t+1)` and the remaining prior mass is `1/(t+1)`. If `A_t=Σ_{s≤t}w_sΠ_{i=s}^tL_i`, then `A_t=L_t(A_{t−1}+1/[t(t+1)])`; adding the tail gives `E_t=A_t+1/(t+1)`. Under C8, fixed mixture components give a nonnegative supermartingale. Ville threshold is `1/α`; at `α=1/20`, it is 20.

## C10 lower rounding

With nonnegative operands, replacing a factor and start/tail weight by their floors at scale `Q`, and flooring each product divided by `Q`, cannot increase the represented value. By induction the fixed-point mixture remains below the exact mixture. It may miss a crossing. This argument assumes no overflow/wraparound and does not prove an unspecified fixed-width implementation.

## C11 Freedman form

If `W_i=log L_i`, `E[W_i|F_(i−1)]≥μ`, `Var(W_i|F_(i−1))≤v`, and `|W_i−E[W_i|F_(i−1)]|≤c`, then for `nμ>A`, Freedman’s lower tail gives `P(ΣW_i<A)≤exp(−(nμ−A)^2/(2(nv+c(nμ−A)/3)))`. Take `A=log(1/α)` for a fixed start. For a mixture component of prior weight `w_s`, crossing its threshold `1/(αw_s)` is sufficient, giving `A_s=log(1/(αw_s))`. The result is conditional and sufficient, not expected or observed delay. The saved numeric first-crossing values were not recalculated here.
