/************************************************************************
*
*	FILENAME		:	sdec_tet.c
*
*	DESCRIPTION		:	Main routines for speech source decoding
*
************************************************************************
*
*	SUB-ROUTINES	:	- Init_Decod_Tetra()
*					- Decod_Tetra()
*
************************************************************************
*
*	INCLUDED FILES	:	source.h
*
************************************************************************/

#include "source.h"

/*--------------------------------------------------------*
 *       Decoder constants parameters.                    *
 *                                                        *
 *   L_frame     : Frame size.                            *
 *   L_subfr     : Sub-frame size.                        *
 *   p           : LPC order.                             *
 *   pp1         : LPC order+1                            *
 *   pit_min     : Minimum pitch lag.                     *
 *   pit_max     : Maximum pitch lag.                     *
 *   L_inter     : Length of filter for interpolation     *
 *   parm_size   : Lenght of vector parm[]                *
 *--------------------------------------------------------*/

#define  L_frame  (Word16)240
#define  L_subfr  (Word16)60
#define  p        (Word16)10
#define  pp1      (Word16)11
#define  pit_min  (Word16)20
#define  pit_max  (Word16)143
#define  L_inter  (Word16)15
#define  parm_size (Word16)23


/*--------------------------------------------------------*
 *   LPC bandwidth expansion factors for noise filter.    *
 *      In Q15 = 0.75, 0.85                               *
 *--------------------------------------------------------*/

#define gamma3  (Word16)24576
#define gamma4  (Word16)27853


/*--------------------------------------------------------*
 *         Static memory allocation.                      *
 *--------------------------------------------------------*/

        /* Excitation vector */

static Word16 old_exc[L_frame+pit_max+L_inter];
static Word16 *exc;

        /* Spectral expansion factors */

static Word16 F_gamma3[p];
static Word16 F_gamma4[p];

        /* Lsp (Line spectral pairs in the cosine domain) */

static Word16 lspold[p]={
              30000, 26000, 21000, 15000, 8000, 0,
		  -8000,-15000,-21000,
			-26000};
static Word16 lspnew[p];

	  /* Initial lsp values used after each time */
        /* a reset is executed */

static Word16 lspold_init[p]={
              30000, 26000, 21000, 15000, 8000, 0,
		  -8000,-15000,-21000,-26000};

        /* Filter's memory */

static Word16 mem_syn[p];

        /* Default parameters */

static Word16 old_parm[parm_size], old_T0;

       /* Global definition */

Word16 last_ener_cod;
Word16 last_ener_pit;


/**************************************************************************
*
*	ROUTINE				:	Init_Decod_Tetra
*
*	DESCRIPTION			:	Initialization of variables for the speech decoder
*
**************************************************************************
*
*	USAGE				:	Init_Decod_Tetra()
*
*	INPUT ARGUMENT(S)		:	None
*
*	OUTPUT ARGUMENT(S)		:	None
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Init_Decod_Tetra(void)
{
  Word16 i;

  old_T0 = 60;
  for(i=0; i<23; i++)
     old_parm[i] = 0;

  /* Initialize static pointer */

  exc    = old_exc + pit_max + L_inter;

  /* Initialize global variables */

  last_ener_cod = 0;
  last_ener_pit = 0;
  
  /* Static vectors to zero */

  for(i=0; i<pit_max + L_inter; i++)
    old_exc[i] = 0;

  for(i=0; i<p; i++)
    mem_syn[i] = 0;


  /* Initialisation of lsp values for first */
  /* frame lsp interpolation */

  for(i=0; i<p; i++)
    lspold[i] = lspold_init[i];


  /* Compute LPC spectral expansion factors */

  Fac_Pond(gamma3, F_gamma3);
  Fac_Pond(gamma4, F_gamma4);

 return;
}


/**************************************************************************
*
*	ROUTINE				:	Decod_Tetra
*
*	DESCRIPTION			:	Main speech decoder function
*
**************************************************************************
*
*	USAGE				:	Decod_Tetra(parm,synth)
*							(Routine_Name(input1,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : Synthesis parameters
*							- Format : 24 * 16 bit-samples
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Synthesis
*							- Format : 240 * 16 bit-samples
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Decod_Tetra(Word16 parm[], Word16 synth[])
{
  /* LPC coefficients */

  Word16 A_t[(pp1)*4];		/* A(z) unquantized for the 4 subframes */
  Word16 Ap3[pp1];		/* A(z) with spectral expansion         */
  Word16 Ap4[pp1];		/* A(z) with spectral expansion         */
  Word16 *A;			/* Pointer on A_t                       */

  /* Other vectors */

  Word16 zero_F[L_subfr+64],  *F;
  Word16 code[L_subfr+4];

  /* Scalars */

  Word16 i, i_subfr;
  Word16 T0, T0_min, T0_max, T0_frac;
  Word16 gain_pit, gain_code, index;
  Word16 sign_code, shift_code;
  Word16 bfi, temp;
  Word32 L_temp;

  /* Initialization of F */

  F  = &zero_F[64];
  for(i=0; i<64; i++)
   zero_F[i] = 0;

  /* Test bfi */

  bfi = *parm++;

  if(bfi == 0)
  {
    D_Lsp334(&parm[0], lspnew, lspold);	/* lsp decoding   */

    for(i=0; i< parm_size; i++)		/* keep parm[] as old_parm */
      old_parm[i] = parm[i];
  }
  else
  {
    for(i=1; i<p; i++)
      lspnew[i] = lspold[i];

    for(i=0; i< parm_size; i++)		/* use old parm[] */
      parm[i] = old_parm[i];
  }

  parm += 3;			/* Advance synthesis parameters pointer */

  /* Interpolation of LPC for the 4 subframes */

  Int_Lpc4(lspold,   lspnew,   A_t);

  /* update the LSPs for the next frame */

  for(i=0; i<p; i++)
    lspold[i]   = lspnew[i];

/*------------------------------------------------------------------------*
 *          Loop for every subframe in the analysis frame                 *
 *------------------------------------------------------------------------*
 * The subframe size is L_subfr and the loop is repeated L_frame/L_subfr  *
 *  times                                                                 *
 *     - decode the pitch delay                                           *
 *     - decode algebraic code                                            *
 *     - decode pitch and codebook gains                                  *
 *     - find the excitation and compute synthesis speech                 *
 *------------------------------------------------------------------------*/

  A = A_t;				/* pointer to interpolated LPC parameters */

  for (i_subfr = 0; i_subfr < L_frame; i_subfr += L_subfr)
  {

    index = *parm++;				/* pitch index */

    if (i_subfr == 0)				/* if first subframe */
    {
      if (bfi == 0)
      {						/* if bfi == 0 decode pitch */
         if (index < 197)
         {
           /* T0 = (index+2)/3 + 19; T0_frac = index - T0*3 + 58; */

           i = add(index, (Word16)2);
           i = mult(i, (Word16)10923);	/* 10923 = 1/3 in Q15 */
           T0 = add(i, (Word16)19);

           i = add(T0, add(T0, T0) );	/* T0*3 */
           i = sub((Word16)58, (Word16)i);
           T0_frac = add(index, (Word16)i);
         }
         else
         {
           T0 = sub(index, (Word16)112);
           T0_frac = 0;
         }
      }
      else   /* bfi == 1 */
      {
        T0 = old_T0;
        T0_frac = 0;
      }


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

    else  /* other subframes */

    {
      if (bfi == 0)				/* if bfi == 0 decode pitch */
      {
         /* T0 = (index+2)/3 - 1 + T0_min; */

         i = add(index, (Word16)2);
         i = mult(i, (Word16)10923);	/* 10923 = 1/3 in Q15 */
         i = sub(i, (Word16)1);
         T0 = add(T0_min, i);

         /* T0_frac = index - 2 - i*3; */

         i = add(i, add(i,i) );		/* i*3 */
         T0_frac = sub( index , add(i, (Word16)2) );
      }
    }

   /*-------------------------------------------------*
    * - Find the adaptive codebook vector.            *
    *-------------------------------------------------*/

    Pred_Lt(&exc[i_subfr], T0, T0_frac, L_subfr);

   /*-----------------------------------------------------*
    * - Compute noise filter F[].                         *
    * - Decode codebook sign and index.                   *
    * - Find the algebraic codeword.                      *
    *-----------------------------------------------------*/

    Pond_Ai(A, F_gamma3, Ap3);
    Pond_Ai(A, F_gamma4, Ap4);

    for (i = 0;   i <= p;      i++) F[i] = Ap3[i];
    for (i = pp1; i < L_subfr; i++) F[i] = 0;

    Syn_Filt(Ap4, F, F, L_subfr, &F[pp1], (Word16)0);

    /* Introduce pitch contribution with fixed gain of 0.8 to F[] */

    for (i = T0; i < L_subfr; i++)
    {
      temp = mult(F[i-T0], (Word16)26216);
      F[i] = add(F[i], temp);
    }

    index = *parm++;
    sign_code  = *parm++;
    shift_code = *parm++;

    D_D4i60(index, sign_code, shift_code, F, code);


   /*-------------------------------------------------*
    * - Decode pitch and codebook gains.              *
    *-------------------------------------------------*/

    index = *parm++;        /* index of energy VQ */

    Dec_Ener(index,bfi,A,&exc[i_subfr],code, L_subfr, &gain_pit, &gain_code);

   /*-------------------------------------------------------*
    * - Find the total excitation.                          *
    * - Find synthesis speech corresponding to exc[].       *
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

    Syn_Filt(A, &exc[i_subfr], &synth[i_subfr], L_subfr, mem_syn, (Word16)1);

    A  += pp1;    /* interpolated LPC parameters for next subframe */
  }

 /*--------------------------------------------------*
  * Update signal for next frame.                    *
  * -> shift to the left by L_frame  exc[]           *
  *--------------------------------------------------*/

  for(i=0; i<pit_max+L_inter; i++)
    old_exc[i] = old_exc[i+L_frame];

  old_T0 = T0;

  return;
}

