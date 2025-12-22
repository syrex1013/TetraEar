/************************************************************************
*
*	FILENAME		:	scod_tet.c
*
*	DESCRIPTION		:	Main routines for speech source encoding
*
************************************************************************
*
*	SUB-ROUTINES	:	- Init_Coder_Tetra()
*					- Coder_Tetra()
*
************************************************************************
*
*	INCLUDED FILES	:	source.h
*
************************************************************************/

#include "source.h"

/*----------------------------------------------------------------------*
 *         Coder constant parameters.                                   *
 *                                                                      *
 *   L_window    : LPC analysis window size.                            *
 *   L_next      : Samples of next frame needed for autocor.            *
 *   L_frame     : Frame size.                                          *
 *   L_subfr     : Sub-frame size.                                      *
 *   p           : LPC order.                                           *
 *   pp1         : LPC order+1                                          *
 *   L_total     : Total speech size.                                   *
 *   dim_rr      : Dimension of matrix rr[][].                          *
 *   pit_min     : Minimum pitch lag.                                   *
 *   pit_max     : Maximum pitch lag.                                   *
 *   L_inter     : Length of filter for interpolation                   *
 *----------------------------------------------------------------------*/

#define  L_window (Word16)256
#define  L_next   (Word16)40
#define  L_frame  (Word16)240
#define  L_subfr  (Word16)60
#define  p        (Word16)10
#define  pp1      (Word16)11
#define  L_total  (Word16)(L_frame+L_next+p)
#define  dim_rr   (Word16)32
#define  pit_min  (Word16)20
#define  pit_max  (Word16)143
#define  L_inter  (Word16)15

/*--------------------------------------------------------*
 *   LPC bandwidth expansion factors.                     *
 *      In Q15 = 0.95, 0.60, 0.75, 0.85                   *
 *--------------------------------------------------------*/

#define gamma1  (Word16)31130
#define gamma2  (Word16)19661
#define gamma3  (Word16)24576
#define gamma4  (Word16)27853


/*--------------------------------------------------------*
 *         Static memory allocation.                      *
 *--------------------------------------------------------*/

        /* Speech vector */

static Word16 old_speech[L_total];
static Word16 *speech, *p_window;
Word16 *new_speech;                    /* Global variable */

        /* Weighted speech vector */

static Word16 old_wsp[L_frame+pit_max];
static Word16 *wsp;

        /* Excitation vector */

static Word16 old_exc[L_frame+pit_max+L_inter];
static Word16 *exc;

        /* All-zero vector */

static Word16 ai_zero[L_subfr+pp1];
static Word16 *zero;

        /* Spectral expansion factors */

static Word16 F_gamma1[p];
static Word16 F_gamma2[p];
static Word16 F_gamma3[p];
static Word16 F_gamma4[p];

        /* Lsp (Line Spectral Pairs in the cosine domain) */

static Word16 lspold[p]={
              30000, 26000, 21000, 15000, 8000, 0,
		  -8000,-15000,-21000,-26000};
static Word16 lspnew[p];
static Word16 lspnew_q[p], lspold_q[p];

	  /* Initial lsp values used after each time */
        /* a reset is executed */

static Word16 lspold_init[p]={
              30000, 26000, 21000, 15000, 8000, 0,
		  -8000,-15000,-21000,-26000};

        /* Filters memories */

static Word16 mem_syn[p], mem_w0[p], mem_w[p];

        /* Matrix rr[dim_rr][dim_rr] */

static Word16 rr[dim_rr][dim_rr];
 
       /* Global definition */

Word16 last_ener_cod;
Word16 last_ener_pit;


/**************************************************************************
*
*	ROUTINE				:	Init_Coder_Tetra
*
*	DESCRIPTION			:	Initialization of variables for the speech encoder
*
**************************************************************************
*
*	USAGE				:	Init_Coder_Tetra()
*
*	INPUT ARGUMENT(S)		:	None
*
*	OUTPUT ARGUMENT(S)		:	None
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Init_Coder_Tetra(void)
{
  Word16 i,j;


/*-----------------------------------------------------------------------*
 *      Initialize pointers to speech vector.                            *
 *                                                                       *
 *                                                                       *
 *   |--------------------|--------|--------|......|-------|-------|     *
 *     previous speech       sf1      sf2             sf4    L_next      *
 *                                                                       *
 *   <----------------  Total speech vector (L_total)   ----------->     *
 *   |           <----  LPC analysis window (L_window)  ----------->     *
 *   |           |        <---- present frame (L_frame) --->             *
 *  old_speech   |        |       <----- new speech (L_frame) ----->     *
 *            p_window    |       |                                      *
 *                     speech     |                                      *
 *                             new_speech                                *
 *-----------------------------------------------------------------------*/

  new_speech = old_speech + L_total - L_frame;	/* New speech     */
  speech     = new_speech - L_next;			/* Present frame  */
  p_window   = old_speech + L_total - L_window;	/* For LPC window */

  /* Initialize global variables */

  last_ener_cod = 0;
  last_ener_pit = 0;
  
  /* Initialize static pointers */

  wsp    = old_wsp + pit_max;
  exc    = old_exc + pit_max + L_inter;
  zero   = ai_zero + pp1;


  /* Static vectors to zero */

  for(i=0; i<L_total; i++)
    old_speech[i] = 0;

  for(i=0; i<pit_max + L_inter; i++)
    old_exc[i] = old_wsp[i] = 0;

  for(i=0; i<p; i++)
    mem_syn[i] = mem_w[i] = mem_w0[i] = 0;

  for(i=0; i<L_subfr; i++)
    zero[i] = 0;

  for(i=0; i< dim_rr; i++)
    for(j=0; j< dim_rr; j++)
    rr[i][j] = 0;

  /* Initialisation of lsp values for first */
  /* frame lsp interpolation */

  for(i=0; i<p; i++)
    lspold_q[i] = lspold[i] = lspold_init[i];

  /* Compute LPC spectral expansion factors */

  Fac_Pond(gamma1, F_gamma1);
  Fac_Pond(gamma2, F_gamma2);
  Fac_Pond(gamma3, F_gamma3);
  Fac_Pond(gamma4, F_gamma4);

 return;
}


/**************************************************************************
*
*	ROUTINE				:	Coder_Tetra
*
*	DESCRIPTION			:	Main speech coder function
*
**************************************************************************
*
*	USAGE				:	Coder_Tetra(ana,synth)
*							(Routine_Name(output1,output2))
*
*	INPUT ARGUMENT(S)		:	None
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Analysis parameters
*							- Format : 23 * 16 bit-samples
*
*		OUTPUT2			:	- Description : Local synthesis
*							- Format : 240 * 16 bit-samples
*
*	RETURNED VALUE		:	None
*
*	COMMENTS			:	- 240 speech data should have been copied to vector
*						new_speech[].  This vector is global and is declared in
*						this function.
*						- Output2 is for debugging only
*
**************************************************************************/

void Coder_Tetra(Word16 ana[], Word16 synth[])
{

  /* LPC coefficients */

  Word16 r_l[pp1], r_h[pp1];	/* Autocorrelations low and high        */
  Word16 A_t[(pp1)*4];		/* A(z) unquantized for the 4 subframes */
  Word16 Aq_t[(pp1)*4];		/* A(z)   quantized for the 4 subframes */
  Word16 Ap1[pp1];		/* A(z) with spectral expansion         */
  Word16 Ap2[pp1];		/* A(z) with spectral expansion         */
  Word16 Ap3[pp1];		/* A(z) with spectral expansion         */
  Word16 Ap4[pp1];		/* A(z) with spectral expansion         */
  Word16 *A, *Aq;			/* Pointer on A_t and Aq_t              */

  /* Other vectors */

  Word16 h1[L_subfr];
  Word16 zero_h2[L_subfr+64], *h2;
  Word16 zero_F[L_subfr+64],  *F;
  Word16 res[L_subfr];
  Word16 xn[L_subfr];
  Word16 xn2[L_subfr];
  Word16 dn[L_subfr+4];
  Word16 code[L_subfr+4];
  Word16 y1[L_subfr];
  Word16 y2[L_subfr];



  /* Scalars */

  Word16 i, i_subfr;
  Word16 T0, T0_min, T0_max, T0_frac;
  Word16 gain_pit, gain_code, index;
  Word16 sign_code, shift_code;
  Word16 temp;
  Word32 L_temp;

  /* Initialization of F and h2 */

  F  = &zero_F[64];
  h2 = &zero_h2[64];
  for(i=0; i<64; i++)
   zero_F[i] = zero_h2[i] = 0;

/*------------------------------------------------------------------------*
 *  - Perform LPC analysis:                                               *
 *       * autocorrelation + lag windowing                                *
 *       * Levinson-Durbin algorithm to find a[]                          *
 *       * convert a[] to lsp[]                                           *
 *       * quantize and code the LSPs                                     *
 *       * find the interpolated LSPs and convert to a[] for all          *
 *         subframes (both quantized and unquantized)                     *
 *------------------------------------------------------------------------*/

  Autocorr(p_window, p, r_h, r_l);		/* Autocorrelations */

  Lag_Window(p, r_h, r_l);			/* Lag windowing    */

  Levin_32(r_h, r_l, A_t);			/* Levinson-Durbin  */

  Az_Lsp(A_t, lspnew, lspold);		/* From A(z) to lsp */

  Clsp_334(lspnew, lspnew_q, ana);		/* Lsp quantization */

  ana += 3;				/* Increment analysis parameters pointer */

  /* Interpolation of LPC for the 4 subframes */

  Int_Lpc4(lspold,   lspnew,   A_t);
  Int_Lpc4(lspold_q, lspnew_q, Aq_t);

  /* update the LSPs for the next frame */

  for(i=0; i<p; i++)
  {
    lspold[i]   = lspnew[i];
    lspold_q[i] = lspnew_q[i];
  }


 /*----------------------------------------------------------------------*
  * - Find the weighted input speech wsp[] for the whole speech frame    *
  * - Find open-loop pitch delay                                         *
  * - Set the range for searching closed-loop pitch                      *
  *----------------------------------------------------------------------*/

  A = A_t;
  for (i = 0; i < L_frame; i += L_subfr)
  {
    Pond_Ai(A, F_gamma1, Ap1);
    Pond_Ai(A, F_gamma2, Ap2);
    Residu(Ap1, &speech[i], &wsp[i], L_subfr);
    Syn_Filt(Ap2, &wsp[i], &wsp[i], L_subfr, mem_w, (Word16)1);
    A += pp1;
  }

  /* Find open loop pitch delay */

  T0 = Pitch_Ol_Dec(wsp, L_frame);

  /* range for closed loop pitch search */

  T0_min = sub(T0, (Word16)2);
  if (T0_min < pit_min) T0_min = pit_min;
  T0_max = add(T0_min, (Word16)4);
  if (T0_max > pit_max)
  {
     T0_max = pit_max;
     T0_min = sub(T0_max, (Word16)4);
  }


 /*------------------------------------------------------------------------*
  *          Loop for every subframe in the analysis frame                 *
  *------------------------------------------------------------------------*
  *  To find the pitch and innovation parameters. The subframe size is     *
  *  L_subfr and the loop is repeated L_frame/L_subfr times.               *
  *     - find the weighted LPC coefficients                               *
  *     - find the LPC residual signal res[]                               *
  *     - compute the target signal for pitch search                       *
  *     - compute impulse response of weighted synthesis filter (h1[])     *
  *     - find the closed-loop pitch parameters                            *
  *     - encode the pitch delay                                           *
  *     - update the impulse response h1[] by including fixed-gain pitch   *
  *     - find the autocorrelations of h1[] (rr[][])                       *
  *     - find target vector for codebook search                           *
  *     - backward filtering of target vector                              *
  *     - codebook search                                                  *
  *     - encode codebook address                                          *
  *     - VQ of pitch and codebook gains                                   *
  *     - find synthesis speech                                            *
  *     - update states of weighting filter                                *
  *------------------------------------------------------------------------*/

  Aq = Aq_t;	/* pointer to interpolated quantized LPC parameters */

  for (i_subfr = 0;  i_subfr < L_frame; i_subfr += L_subfr)
  {

 
   /*---------------------------------------------------------------*
     * Find the weighted LPC coefficients for the weighting filter.  *
     *---------------------------------------------------------------*/

    Pond_Ai(Aq, F_gamma3, Ap3);
    Pond_Ai(Aq, F_gamma4, Ap4);


    /*---------------------------------------------------------------*
     * Compute impulse response, h1[], of weighted synthesis filter  *
     *---------------------------------------------------------------*/

    ai_zero[0] = 4096;				/* 1 in Q12 */
    for (i = 1; i <= p; i++) ai_zero[i] = 0;

    Syn_Filt(Ap4, ai_zero, h1, L_subfr, zero, (Word16)0);

    /*---------------------------------------------------------------*
     * Compute LPC residual and copy it to exc[i_subfr]              *
     *---------------------------------------------------------------*/

    Residu(Aq, &speech[i_subfr], res, L_subfr);

    for(i=0; i<L_subfr; i++) exc[i_subfr+i] = res[i];

    /*---------------------------------------------------------------*
     * Find the target vector for pitch search:  ->xn[]              *
     *---------------------------------------------------------------*/

    Syn_Filt(Ap4, res, xn, L_subfr, mem_w0, (Word16)0);

    /*----------------------------------------------------------------------*
     *                 Closed-loop fractional pitch search                  *
     *----------------------------------------------------------------------*
     * The pitch range for the first subframe is divided as follows:        *
     *   19 1/3  to   84 2/3   resolution 1/3                               *
     *   85      to   143      resolution 1                                 *
     *                                                                      *
     * The period in the first subframe is encoded with 8 bits.             *
     * For the range with fractions:                                        *
     *   code = (T0-19)*3 + frac - 1;   where T0=[19..85] and frac=[-1,0,1] *
     * and for the integer only range                                       *
     *   code = (T0 - 85) + 197;        where T0=[86..143]                  *
     *----------------------------------------------------------------------*
     * For other subframes: if t0 is the period in the first subframe then  *
     * T0_min=t0-5   and  T0_max=T0_min+9   and  the range is given by      *
     *      T0_min-1 + 1/3   to  T0_max + 2/3                               *
     *                                                                      *
     * The period in the 2nd,3rd,4th subframe is encoded with 5 bits:       *
     *  code = (T0-(T0_min-1))*3 + frac - 1;  where T0[T0_min-1 .. T0_max+1]*
     *---------------------------------------------------------------------*/

    T0 = Pitch_Fr(&exc[i_subfr], xn, h1, L_subfr, T0_min, T0_max,
                  i_subfr, &T0_frac);

    if (i_subfr == 0)
    {
      /* encode pitch delay (with fraction) */

      if (T0 <= 85)
      {
        /* index = T0*3 - 58 + T0_frac; */
        index = add(T0, add(T0, T0));
        index = sub(index, (Word16)58);
        index = add(index, T0_frac);
      }
      else
        index = add(T0, (Word16)112);


      /* find T0_min and T0_max for other subframes */

      T0_min = sub(T0, (Word16)5);
      if (T0_min < pit_min) T0_min = pit_min;
      T0_max = add(T0_min, (Word16)9);
      if (T0_max > pit_max)
      {
        T0_max = pit_max;
        T0_min = sub(T0_max, (Word16)9);
      }
    }

    else						/* other subframes */
    {
      i = sub(T0, T0_min);
							/* index = i*3 + 2 + T0_frac;  */
      index = add(i, add(i, i));
      index = add(index, (Word16)2);
      index = add(index, T0_frac);
    }

    *ana++ = index;


   /*-----------------------------------------------------------------*
    *   - find unity gain pitch excitation (adaptive codebook entry)  *
    *     with fractional interpolation.                              *
    *   - find filtered pitch exc. y1[]=exc[] filtered by 1/Ap4(z)    *
    *   - compute pitch gain and limit between 0 and 1.2              *
    *   - update target vector for codebook search                    *
    *-----------------------------------------------------------------*/


    Pred_Lt(&exc[i_subfr], T0, T0_frac, L_subfr);

    Syn_Filt(Ap4, &exc[i_subfr], y1, L_subfr, zero, (Word16)0);

    gain_pit = G_Pitch(xn, y1, L_subfr);

	/* xn2[i] = xn[i] - y1[i]*gain_pit */

    for (i = 0; i < L_subfr; i++)
    {
      L_temp = L_mult(y1[i], gain_pit);
      L_temp = L_shl(L_temp, (Word16)3);	/* gain_pit in Q12 */
      L_temp = L_sub( Load_sh16(xn[i]), L_temp);
      xn2[i] = extract_h(L_temp);
    }


   /*----------------------------------------------------------------*
    * -Compute impulse response F[] and h2[] for innovation codebook *
    * -Find correlations of h2[];  rr[i][j] = sum h2[n-i]*h2[n-j]    *
    *----------------------------------------------------------------*/

    for (i = 0; i <= p; i++) ai_zero[i] = Ap3[i];
    Syn_Filt(Ap4, ai_zero, F, L_subfr, zero, (Word16)0);

    /* Introduce pitch contribution with fixe gain of 0.8 to F[] */

    for (i = T0; i < L_subfr; i++)
    {
      temp = mult(F[i-T0], (Word16)26216);
      F[i] = add(F[i], temp);
    }

    /* Compute h2[]; -> F[] filtered by 1/Ap4(z) */

    Syn_Filt(Ap4, F, h2, L_subfr, zero, (Word16)0);

    Cal_Rr2(h2, (Word16*)rr);

   /*-----------------------------------------------------------------*
    * - Backward filtering of target vector (find dn[] from xn2[])    *
    * - Innovative codebook search (find index and gain)              *
    *-----------------------------------------------------------------*/

    Back_Fil(xn2, h2, dn, L_subfr);	/* backward filtered target vector dn */

    *ana++ =D4i60_16(dn,F,h2, rr, code, y2, &sign_code, &shift_code);
    *ana++ = sign_code;
    *ana++ = shift_code;
    gain_code = G_Code(xn2, y2, L_subfr);

   /*-----------------------------------------------------------------*
    * - Quantization of gains.                                        *
    *-----------------------------------------------------------------*/

    *ana++ = Ener_Qua(Aq,&exc[i_subfr],code, L_subfr, &gain_pit, &gain_code);

   /*-------------------------------------------------------*
    * - Find the total excitation                           *
    * - Update filter memory mem_w0 for finding the target  *
    *   vector in the next subframe.                        *
    *   The filter state mem_w0[] is found by filtering by  *
    *   1/Ap4(z) the error between res[i] and exc[i]        *
    *-------------------------------------------------------*/

    for (i = 0; i < L_subfr;  i++)
    {
      /* exc[i] = gain_pit*exc[i] + gain_code*code[i]; */
      /* exc[i]  in Q0   gain_pit in Q12               */
      /* code[i] in Q12  gain_cod in Q0                */
      L_temp = L_mult0(exc[i+i_subfr], gain_pit);
      L_temp = L_mac0(L_temp, code[i], gain_code);
      exc[i+i_subfr] = L_shr_r(L_temp, (Word16)12);
    }

    for(i=0; i<L_subfr; i++)
      res[i] = sub(res[i], exc[i_subfr+i]);

    Syn_Filt(Ap4, res, code, L_subfr, mem_w0, (Word16)1);

   /* Note: we use vector code[] as output only as temporary vector */

   /*-------------------------------------------------------*
    * - find synthesis speech corresponding to exc[]        *
    *   This filter is to help debug only.                  *
    *-------------------------------------------------------*/

    Syn_Filt(Aq, &exc[i_subfr], &synth[i_subfr], L_subfr, mem_syn,
			(Word16)1);

    Aq += pp1;
  }

 /*--------------------------------------------------*
  * Update signal for next frame.                    *
  * -> shift to the left by L_frame:                 *
  *     speech[], wsp[] and  exc[]                   *
  *--------------------------------------------------*/

  for(i=0; i< L_total-L_frame; i++)
    old_speech[i] = old_speech[i+L_frame];

  for(i=0; i<pit_max; i++)
    old_wsp[i] = old_wsp[i+L_frame];

  for(i=0; i<pit_max+L_inter; i++)
    old_exc[i] = old_exc[i+L_frame];

  return;
}

