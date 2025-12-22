/************************************************************************
*
*	FILENAME		:	sub_sc_d.c
*
*	DESCRIPTION		:	Source coder/decoder sub-routines used in the 
*					TETRA speech codec
*
************************************************************************
*
*	SUB-ROUTINES	:	- Bits2prm_Tetra()
*					- Cal_Rr2()
*					- Clsp_334()
*					- Dec_Ener()
*					- D4i60_16()
*					- D_D4i60()
*					- D_Lsp334()
*					- Ener_Qua()
*					- G_Code()
*					- G_Pitch()
*					- Inter8_M1_3()
*					- Inter8_1_3()
*					- Inter32_M1_3()
*					- Inter32_1_3()
*					- Lag_Max()
*					- Norm_Corr()
*					- Pitch_Fr()
*					- Pitch_Ol_Dec()
*					- Post_Process()
*					- Pred_Lt()
*					- Pre_Process() (including Init_Pre_Process)
*					- Prm2bits_Tetra()
*
************************************************************************
*
*	INCLUDED FILES	:	source.h
*
*					clsp_334.tab
*					ener_qua.tab
*
************************************************************************/

#include "source.h"

#include "clsp_334.tab"
#include "ener_qua.tab"


/**************************************************************************
*
*	ROUTINE				:	Bits2prm_Tetra
*
*	DESCRIPTION			:	Convert serial received bits to the encoder
*							parameter vector
*
**************************************************************************
*
*	USAGE				:	Bits2prm_Tetra(buffer_in,buffer_out)
*							(Routine_Name(input1,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : Serial bits (137 + bfi)
*							- Format : Word16 - .. * 16 bit-samples
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Encoded parameters  
*								         (23 parameters + bfi)
*							- Format : Word16 - .. * 16 bit-samples
*
*	RETURNED VALUE		:	None
*
*	COMMENTS			:	The received parameters are :
*
*						- BFI	bad frame indicator		1 bit
*
*						- LSP	1st codebook 			8 bits
*							2nd codebook			9 bits
*							3nd codebook			9 bits
*
*						- for the 4 subframes :
*							pitch delay			8 bits (first)
*											5 bits (others)
*							codebook index		14 bits
*							pulse global sign		1 bit
*							pulse shift			1 bit
*							pitch and innovation gains	6 bits
*
**************************************************************************/

#define PRM_NO 23

void Bits2prm_Tetra(Word16 *bits, Word16 prm[])
{
  Word16 i;
  static Word16 bitno[PRM_NO] = {8, 9, 9,            /* split VQ LSP  */
                                 8, 14, 1, 1, 6,     /* subframe 1    */
                                 5, 14, 1, 1, 6,     /* subframe 2    */
                                 5, 14, 1, 1, 6,     /* subframe 3    */
                                 5, 14, 1, 1, 6};    /* subframe 4    */
  *prm++ = *bits++;     /* read BFI */

  for (i = 0; i < PRM_NO; i++)
  {
    prm[i] = bin2int(bitno[i], bits);
    bits  += bitno[i];
  }
}

/**************************************************************************
*
*	ROUTINE				:	Cal_Rr2
*
*	DESCRIPTION			:	Compute the autocorrelation matrix of 
*						impulse response h
*							Only the even elements are stored in the matrix
*
**************************************************************************
*
*	USAGE				:	Cal_Rr2(buffer_1,buffer_2)
*							(Routine_Name(input1,input2))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : Impulse response
*						- Format : Word16
*
*		INPUT2			:	- Description : Autocorrelation matrix
*								          (passed as a vector)
*							- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	None
*
*	RETURNED VALUE		:	None
*
*	COMMENTS			:	Matrice rr[dim_rr][dim_rr]
*
*							<------- dim_rr ------->
*							<------ L/2 ---->
*
*						^	x x x x x x ... x 0 ...  0	^
*						|	x x x x x x ... x 0 ...  0	|
*						|	x x x x x x ... x 0 ...  0	|
*						|	x x x x x x ... x 0 ...  0	|
*						L/2	x x x x x x ... x 0 ...  0	|
*						|	x x x x x x ... x 0 ...  0	dim_rr
*						|	| | | | | |       | |      |	|
*						v	x x x x x x ... x 0 ...  0	|
*							0 0 0 0 0 0 ... 0 0 ... 0	|
*							| | | | | |     | |     |		|
*							0 0 0 0 0 0 ... 0 0 ... 0	v
*
*						Firstly, rr[L/2-1][L/2-1] is computed, with
*						the main diagonal step up. Then, the same
*						is done for the other diagonals.
*
**************************************************************************/

/* Length of subframe = 60 */
#define L      60

/* Dimension of matrix rr[dim_rr][dim_rr]  = 32 */
#define dim_rr 32

/* Increment on diagonal */
#define diag   33

/* Index of last element to compute = rr[L/2-1][L/2-1] = rr[29*32+29] */
#define last   957


void Cal_Rr2(Word16 h[], Word16 *rr)
{
 Word16 i, k, dec;
 Word32 s;
 Word16 *ph, *phd;
 Word16 *rr_fin_c;
 Word16 *rr_fin_r;
 Word16 *rr_ij;
 Word16 *rr_ji;
 Word16 hs[L];

 /* Scaling for maximum precision */

 s = 0;
 for(i=0; i<L; i++)
   s = L_mac0(s, h[i], h[i]);

 k = norm_l(s);
 k = shr(sub(k, (Word16)1), (Word16)1);

 for(i=0; i<L; i++)
  hs[i] = shl(h[i], k);

 /* Compute rr[][] */

 rr_fin_r = &rr[last];                  /* pointer on rr[L/2-1][L/2-1]*/
 rr_fin_c = rr_fin_r;

 for (dec = 0 ;dec < L; dec+=2)
 {
   ph  = hs;                            /* pointer on hs[i]      */
   phd = &hs[dec];                      /* pointer on hs[dec+i]  */
   rr_ij = rr_fin_c;                    /* end of column j       */
   rr_ji = rr_fin_r;                    /* end of row j          */
   s = 0;
   for (k = 0; k < L-dec; k+=2)
   {
     s = L_mac(s, *ph++, *phd++);
     s = L_mac(s, *ph++, *phd++);
     *rr_ij = extract_h(s);
     *rr_ji = extract_h(s);
     rr_ij -= diag;                     /* decrement pointers */
     rr_ji -= diag;
   }
   rr_fin_c--;                          /* decrement column */
   rr_fin_r -= dim_rr;                  /* decrement row    */
 }
 return;
}


/**************************************************************************
*
*	ROUTINE				:	Clsp_334
*
*	DESCRIPTION			:	Split vector quantization of LSP parameters
*							Use a split-3 VQ in the cosine lsp domain (-1,1),
*							without weighting
*
**************************************************************************
*
*	USAGE				:	Clsp_334(buffer_in,buffer_out1,buffer_out2)
*							(Routine_Name(input1,output1,output2))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : LSPs in the cosine domain (-1,1)
*						- Format : Word16 - Q15
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Quantized LSPs in the cosine domain
*						- Format : Word16 - Q15
*
*		OUTPUT2			:	- Description : Indices of the 3 selected 
*								          codebook entries
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
*
**************************************************************************/

void Clsp_334(Word16 *lsp, Word16 *lsp_q, Word16 *indice)
{

 Word16 i, j, ind, temp;
 Word16 *p_dico;
 Word32 min, dist;

 static Word16 lsp_old[10]={
               30000, 26000, 21000, 15000, 8000, 0,
	 	  -8000,-15000,-21000,-26000};


/* Search dico1  lsp[0]-lsp[2] */

 p_dico = dico1_clsp;
 min    = MAX_32;

 for (i = 0; i< taille_dic1; i++)
 {
    temp  = sub(lsp[0], *p_dico++);
    dist = L_mult0(temp,temp);
    for(j=1; j<3; j++)
    {
      temp  = sub(lsp[j], *p_dico++);
      dist  = L_mac0(dist,temp,temp);
    }
    if (L_sub(dist, min) < 0) { min = dist; ind = i; }
 }

 indice[0] = ind;
 p_dico    = &dico1_clsp[ind * 3];
 lsp_q[0]  = *p_dico++ ;
 lsp_q[1]  = *p_dico++ ;
 lsp_q[2]  = *p_dico++ ;

/* Search dico2 lsp[3]-lsp[5] */

 p_dico = dico2_clsp;
 min    = MAX_32;

 for (i = 0; i< taille_dic2; i++)
 {
    temp  = sub(lsp[3], *p_dico++);
    dist  = L_mult0(temp,temp);
    for(j=4; j<6; j++)
    {
      temp  = sub(lsp[j], *p_dico++);
      dist  = L_mac0(dist,temp,temp);
    }
    if (L_sub(dist, min) < 0) { min = dist; ind = i; }
 }

 indice[1] = ind;
 p_dico    = &dico2_clsp[ind * 3];
 lsp_q[3]  = *p_dico++ ;
 lsp_q[4]  = *p_dico++ ;
 lsp_q[5]  = *p_dico++ ;

/* Search dico3 lsp[6]-lsp[9] */

 p_dico = dico3_clsp;
 min    = MAX_32;

 for (i = 0; i< taille_dic3; i++)
 {
    temp  = sub(lsp[6], *p_dico++);
    dist  = L_mult0(temp,temp);
    for(j=7; j<10; j++)
    {
      temp  = sub(lsp[j], *p_dico++);
      dist  = L_mac0(dist,temp,temp);
    }
    if (L_sub(dist, min) < 0) { min = dist; ind = i; }
 }

 indice[2] = ind;
 p_dico    = &dico3_clsp[ind * 4];
 lsp_q[6]  = *p_dico++ ;
 lsp_q[7]  = *p_dico++ ;
 lsp_q[8]  = *p_dico++ ;
 lsp_q[9]  = *p_dico++ ;

 /* Minimum distance between lsp_q[2] and lsp_q[3] */

 temp = 917;                    /* 917 = 0.028 in Q15 = 50hz around 1000hz */
 temp = sub(temp, lsp_q[2]);
 temp = add(temp, lsp_q[3]);    /* temp = 0.028 - (lsp_q[2]-lsp_q[3])      */
 if (temp > 0)
 {
   temp = shr(temp, (Word16)1);
   lsp_q[2] = add(lsp_q[2], temp);
   lsp_q[3] = sub(lsp_q[3], temp);
 }
 /* Minimum distance between lsp_q[5] and lsp_q[6] */

 temp = 1245;                   /* 1245= 0.038 in Q15 = 50hz around 1600hz */
 temp = sub(temp, lsp_q[5]);
 temp = add(temp, lsp_q[6]);    /* temp = 0.038 - (lsp_q[5]-lsp_q[6])      */
 if (temp > 0)
 {
   temp = shr(temp, (Word16)1);
   lsp_q[5] = add(lsp_q[5], temp);
   lsp_q[6] = sub(lsp_q[6], temp);
 }

 /* Verify if lsp_q[] are still in order */

 temp = 0;
 for(i=0; i<9; i++)
 {
    if(sub(lsp_q[i],lsp_q[i+1]) <= 0 )
    {
      temp = 1;
    }
 }

  /* If lsp_q[] are not in order keep old lsp_q[] */

 if(temp != 0)
 {
   for(i=0; i<10; i++)
   lsp_q[i] = lsp_old[i];
 }
 else
 {
   for(i=0; i<10; i++)
   lsp_old[i] = lsp_q[i];
 }
 return;
}

/**************************************************************************
*
*	ROUTINE				:	Dec_Ener
*
*	DESCRIPTION			:	Decode gains of pitch and innovative codebook
*
**************************************************************************
*
*	USAGE				:	Dec_Ener(index,bfi,buffer_in1,buffer_in2,buffer_in3,
*							L_subfr,gain_p,gain_c)
*							(Routine_Name(input1,input2,input3,input4,input5,
*							input6,output1,output2))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Index of energy quantizer
*						- Format : Word16
*
*	INPUT2			:	- Description : Bad frame indicator
*						- Format : Word16
*
*	INPUT3			:	- Description : LPC filter
*						- Format : Word16
*
*	INPUT4			:	- Description : Adaptive codebook
*						- Format : Word16
*
*		INPUT5			:	- Description : Innovation codebook
*							- Format : Word16
*	
*		INPUT6			:	- Description : Subframe length
*							- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Quantized pitch gain
*							- Format : Word16
*
*		OUTPUT2			:	- Description : Quantized code gain
*							- Format : Word16
*
*	RETURNED VALUE		:	Index of energy quantizer
*
**************************************************************************/

  extern Word16 last_ener_pit;
  extern Word16 last_ener_cod;

Word16 Dec_Ener(Word16 index, Word16 bfi, Word16 A[], Word16 prd_lt[],
          Word16 code[], Word16 L_subfr, Word16 *gain_pit, Word16 *gain_cod)
{

  Word16  i, j;
  Word16  exp, frac;
  Word16  exp_lpc, ener_lpc;
  Word16  exp_plt, ener_plt, pred_pit;
  Word16  ener_c, pred_cod;
  Word32  L_tmp;


  /*------------------------------------------------------*
   * Energy of impulse response of 1/A(z) for length = 60 *
   *------------------------------------------------------*/

  L_tmp = Lpc_Gain(A);

  exp_lpc  = norm_l(L_tmp);
  ener_lpc = extract_h( L_shl(L_tmp, exp_lpc) );

  /*-------------------------------*
   * Energy of adaptive codebook   *
   *-------------------------------*/

  L_tmp = 1;				/* Avoid case of all-zeros */

  for(i=0; i<L_subfr; i++)
    L_tmp = L_mac0(L_tmp, prd_lt[i], prd_lt[i]);

  exp_plt  = norm_l(L_tmp);
  ener_plt = extract_h( L_shl(L_tmp, exp_plt) );

  /* ener_plt = Log2(ener_plt * ener_lpc) */

  L_tmp = L_mult0(ener_plt, ener_lpc);
  exp_plt = add(exp_plt, exp_lpc);

  Log2(L_tmp, &exp, &frac);

  L_tmp = Load_sh16(exp);
  L_tmp = add_sh(L_tmp, frac, (Word16)1);	/* Log2(ener_plt*ener_lpc) in Q16*/
  L_tmp = sub_sh16(L_tmp, exp_plt);		/* subtract exponant of ener_plt */

  /* Input on 15 bits */
  L_tmp = add_sh(L_tmp, (Word16)1710, (Word16)8); /* +6.68 in Q16 
									for other scaling    */

  L_tmp = L_shr(L_tmp, (Word16)8);		/* Convert from Q16 to Q8        */
  ener_plt = extract_l(L_tmp);

  /*-------------------------------*
   * Energy coming from code       *
   *-------------------------------*/

  L_tmp = 0;
  for(i=0; i<L_subfr; i++)
    L_tmp = L_mac0(L_tmp, code[i], code[i]);

  ener_c = extract_h(L_tmp);

  /* ener_c = Log2(ener_c * ener_lpc) */

  L_tmp = L_mult0(ener_c, ener_lpc);

  Log2(L_tmp, &exp, &frac);

  L_tmp = Load_sh16(exp);
  L_tmp = add_sh(L_tmp, frac, (Word16)1);	/* Log2(ener_plt*ener_lpc) in Q16*/
  L_tmp = sub_sh16(L_tmp, exp_lpc);		/* subtract exponant of ener_lpc */

  /* Input on 15 bits */
  L_tmp = sub_sh(L_tmp, (Word16)4434, (Word16)8); /*-17.32 in Q16 
									for other scaling    */

  L_tmp = L_shr(L_tmp, (Word16)8);		/* Convert from Q16 to Q8        */
  ener_c = extract_l(L_tmp);


  /*-----------------------------------------------*
   * Test for bfi.                                 *
   *                                               *
   *  if (bfi != 0)                                *
   *    ->last_ener_pit -= 0.5                     *
   *    ->last_ener_cod -= 0.5                     *
   *  else                                         *
   *  {                                            *
   *    decode new last_ener_pit et last_ener_cod  *
   *  }                                            *
   *-----------------------------------------------*/

   if(bfi != 0)
   {
     last_ener_pit = sub(last_ener_pit, (Word16)128);	/* -0.5 in Q8 */
     if(last_ener_pit < 0) last_ener_pit = 0;

     last_ener_cod = sub(last_ener_cod, (Word16)128);	/* -0.5 in Q8 */
     if(last_ener_cod < 0) last_ener_cod = 0;
   }
   else
   {

     /*-----------------------------------------------------------------*
      * Prediction on pitch energy.                                     *
      *  pred_pit = 0.50 * last_ener_pit + 0.25 * last_ener_cod - 3.0   *
      *  if(pred_pit < 0.0) pred_pit = 0.0;                             *
      *-----------------------------------------------------------------*/

     L_tmp = Load_sh(last_ener_pit, (Word16)8);	/* .5 last_ener_pit in Q9  */
     L_tmp = add_sh(L_tmp,last_ener_cod, (Word16)7); /*+.25 last_ener_code 
											in Q9    */
     L_tmp = sub_sh(L_tmp, (Word16)768, (Word16)9); /* -3.0 in Q9          */
     if(L_tmp < 0) L_tmp = 0;
     pred_pit = store_hi(L_tmp, (Word16)7);	/* result in Q8 		   */

     /*-----------------------------------------------------------------*
      * Prediction on code energy.                                      *
      *  pred_cod = 0.50 * last_ener_cod + 0.25 * last_ener_pit - 3.0   *
      *  if(pred_cod < 0.0) pred_cod = 0.0;                             *
      *-----------------------------------------------------------------*/

     L_tmp = Load_sh(last_ener_cod, (Word16)8);	/* .5 last_ener_cod in Q9  */
     L_tmp = add_sh(L_tmp, last_ener_pit, (Word16)7); /*+.25 last_ener_pit 
											in Q9    */
     L_tmp = sub_sh(L_tmp, (Word16)768, (Word16)9); /* -3.0 in Q9          */
     if(L_tmp < 0) L_tmp = 0;
     pred_cod = store_hi(L_tmp, (Word16)7);	/* result in Q8		   */

     /*-----------------------------------------------------------------*
      * Read quantized values.                                          *
      *-----------------------------------------------------------------*/

     j = shl(index, (Word16)1);
     last_ener_pit = add(t_qua_ener[j],   pred_pit);
     last_ener_cod = add(t_qua_ener[j+1], pred_cod);

     /* Limit energies ->for transmission errors */

     if(sub(last_ener_pit, (Word16)6912)>0)last_ener_pit = 6912; 
									/* 6912 = 27 in Q8 */
     if(sub(last_ener_cod, (Word16)6400)>0)last_ener_cod = 6400; 
									/* 6400 = 25 in Q8 */
  }


  /*---------------------------------------------------*
   *                                                   *
   *  Compute the quantized pitch gain.                *
   *                                                   *
   *     temp = 0.5 * ( last_ener_pit - ener_plt );    *
   *     temp = pow(2.0, temp);                        *
   *     if( temp > 1.2) temp = 1.2;                   *
   *     *gain_pit = temp;                             *
   *                                                   *
   *---------------------------------------------------*/

  L_tmp = Load_sh(last_ener_pit, (Word16)6);	 /* last_ener_pit/2 in Q15 */
  L_tmp = sub_sh(L_tmp, ener_plt, (Word16)6);	 /* - ener_plt/2    in Q15 */
  L_tmp = add_sh(L_tmp, (Word16)12, (Word16)15); /* to have gain in Q12    */
  L_extract(L_tmp, &exp, &frac);
  L_tmp = pow2(exp, frac);
  if( L_sub(L_tmp, (Word16)4915) > 0) L_tmp = 4915; /* 4915 = 1.2 in Q12   */
  *gain_pit = extract_l(L_tmp);

  /*---------------------------------------------------*
   *                                                   *
   *  Compute the innovative code gain.                *
   *                                                   *
   *     temp = 0.5 * ( last_ener_cod - ener_c );      *
   *     *gain_cod = pow(2.0, temp);                   *
   *                                                   *
   *---------------------------------------------------*/

  L_tmp = Load_sh(last_ener_cod, (Word16)6);	/* last_ener_cod/2 in Q15 */
  L_tmp = sub_sh(L_tmp, ener_c, (Word16)6);	/* - ener_c/2      in Q15 */
  L_extract(L_tmp, &exp, &frac);
  L_tmp = pow2(exp, frac);
  *gain_cod = extract_l(L_tmp);

  return index;
}


/**************************************************************************
*
*	ROUTINE				:	D4i60_16
*
*	DESCRIPTION			:	Innovation codebook search
*
**************************************************************************
*
*	USAGE				:	D4i60_16(buffer_in1,buffer_in2,buffer_in3,buffer_in4,
*							buffer_out1, buffer_out2,sign,shift)
*							(Routine_Name(input1,input2,input3,input4,
*							output1,output2,output3,output4))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Result of backward-filtering
*						- Format : Word16
*
*	INPUT2			:	- Description : Impulse response of noise filter
*							          (vector f[])
*						- Format : Word16 - (must be preceeded by 64 zeros)
*
*	INPUT3			:	- Description : Total impulse response (vector h[])
*						- Format : Word16 - (must be preceeded by 64 zeros)
*
*	INPUT4			:	- Description : Autocorrelations of h[]
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Innovation code found 
*							  by convolving with f[]
*							- Format : Word16
*
*		OUTPUT2			:	- Description : Innovation code found 
*							  by convolving with h[]
*							- Format : Word16
*
*		OUTPUT3			:	- Description : Innovation code gain sign 
*							- Format : Word16
*
*		OUTPUT4			:	- Description : Shift of innovation code 
*							- Format : Word16
*
*	RETURNED VALUE		:	Index of innovation code
*
**************************************************************************


**************************************************************************
*
*	COMMENTS			:	The code length is 60, containing 4 nonzero pulses
*
*						i0, i1, i2, i3, with fixed signs.
*						i0 can take 30 positions.
*						i1, i2 and i3 can have 8 possible positions :
*
*						i0 (+)	: 0,  2, 4.  .... 58
*						i1 (-)	: 2, 10, 18, 26, 34, 42, 50, 58
*						i2 (+)	: 4, 12, 20, 28, 36, 44, 52, (60)
*						i3 (-)	: 6, 14, 22, 30, 38, 46, 54, (62)
*
*						Positions 60 and 62 correspond, respectively,
*						to pulses i2 and i3 not used.
*						The code can be shifted 1 position to the right.
*
*	NOTES ON COMPLEXITY		:
*
*	1 :	In this routine all accesses to matrix rr[][] use indices. This was done for clarity and
*		readability of the program. In the actual real-time implementation all these 
*		accesses use pointers.  Parallel autoincrement of pointers on dn[] and rr[][] 
*		should be used, especially for the two most inner loops in the search which are very
*		critical.
*
*		As the number of addressing registers and the possible modes of autoincrement 
*		can vary with each DSP, the addressing of matrix rr[][] should be optimized 
*		for the DSP used.
*
*	2 :	Because of the thresholds it is difficult to estimate the average complexity.  
*		Usually, we mesure it with the real-time implementation. The worst 
*		case corresponds to "time <= 0".  The decrements of 3 and 4 on variable 
*		"time" come from the relative number of operations when "seuil2" is exceeded and 
*		the number of operations when "seuil1" is exceeded, excluding the operations when
*		"seuil2" is exceeded. We supose that a new maximum is found 1 out of 8 new tries.
*		The numbers 3 and 4 correspond to the real-time implementation and not to this 
*		C code.
*
**************************************************************************/

#define lcode 60

/* Gain for impulse 0 (i0) = sqrt(2) = 1.4142                             */
/* We use different values to be compatible with the implementation       */
/* which uses 3 different Qx formats for this number to simplify scaling. */

#define Q11_gain_i0  2896
#define Q13_gain_i0 11585
#define Q14_gain_i0 23170

/*------------------------------------------------------------------*
 * The next 3 parameters control the time taken by the innovative   *
 * codebook search.                                                 *
 * The first two parameters control if a section of the innovative  *
 * codebook should be search or not. The last parameter controls    *
 * the absolute maximum time used by the innovative codebook search.*
 *------------------------------------------------------------------*/

 /* thresholds = 0.586 in Q15 */

#define threshold1 19200
#define threshold2 19200
#define max_time   350

Word16 D4i60_16(Word16 dn[], Word16 f[], Word16 h[], Word16 rr[][32],
            Word16 cod[], Word16 y[], Word16 *sign, Word16 *shift_code)
{
 Word16 ip0, ip1, ip2, ip3;
 Word16 ii0, ii1, ii2, ii3;
 Word16 *p0, *p1, *p2, *p3;
 Word16 i,j;
 Word16 shif, shift;
 Word16 time, index;
 Word16 ps0,  ps1,  ps2,  ps3;
 Word16 ps0a, ps1a, ps2a;
 Word16 ps, ps3c, psc;
 Word16 alpha, alp1, alp2, alp3;
 Word16 seuil1,seuil2;
 Word16 max0, max1, max2, min0, min1, min2;
 Word32 L_tmp;
 Word32 alp0_32, alp1_32, alp2_32, ps2_32;

 /* set dn[60] - dn[63] to zero */
 dn[60]=dn[61]=dn[62]=dn[63] = 0;

 /* Find min. and max. of dn[] for positions of i0, i1, i2 */

 min0=max0=0;

 for(i = 0; i<60; i += 2)
 {
   j = add(dn[i], dn[i+1]);
   if      (sub(j,max0) > 0) max0 = j;
   else if (sub(j,min0) < 0) min0 = j;
 }
 max0 = shr(max0, (Word16)1);
 min0 = shr(min0, (Word16)1);
 

 /* Multiply max0 and min0 by gain_i0 in Q11 */

 max0 = store_hi(L_mult0(max0, (Word16)Q11_gain_i0), (Word16)5);
 min0 = store_hi(L_mult0(min0, (Word16)Q11_gain_i0), (Word16)5);

 min1=max1=0;
 for(i = 2; i<60; i += 8)
 {
   j = add(dn[i], dn[i+1]);
   if      (sub(j,max1) > 0) max1 = j;
   else if (sub(j,min1) < 0) min1 = j;
 }
 max1 = shr(max1, (Word16)1);
 min1 = shr(min1, (Word16)1);

 min2=max2=0;
 for(i = 4; i<60; i += 8)
 {
   j = add(dn[i], dn[i+1]);
   if      (sub(j,max2) > 0) max2 = j;
   else if (sub(j,min2) < 0) min2 = j;
 }
 max2 = shr(max2, (Word16)1);
 min2 = shr(min2, (Word16)1);


/*----------------------------------------------------------*
 * Find absolute maximum for combination dn[i0] and dn[i1]  *
 *      and for combination dn[i0], dn[i1] and dn[i2]       *
 *   max1 = max ( max0-min1 , max1-min0 )                   *
 *   max2 = max ( max0-min1+max2 , max1-min0-min2 )         *
 *----------------------------------------------------------*/

 max0 = sub(max0, min1);
 max2 = add(max0, max2);
 max1 = sub(max1, min0);
 j    = sub(max1, min2);

 if(sub(max0,max1) > 0) max1 = max0;
 if(sub(j,max2)    > 0) max2 = j;

 /* Set thresholds */
 seuil1 = mult(max1, (Word16)threshold1);
 seuil2 = mult(max2, (Word16)threshold2);

 /* Default values */

 ip0    = 0;
 ip1    = 2;
 ip2    = 4;
 ip3    = 6;
 shift  = 0;
 ps     = 0;
 psc    = 0;
 alpha  = 255;
 time   = max_time;

 /* Four loops to search innovation code. */

 for (ii0=0; ii0<30; ii0++)
 {
   ps0  = store_hi(L_mult0((Word16)Q11_gain_i0, dn[2*ii0]), (Word16)5);
   ps0a = store_hi(L_mult0((Word16)Q11_gain_i0, dn[2*ii0+1]), (Word16)5);
   alp0_32 = Load_sh(rr[ii0][ii0], (Word16)14); 
   
   for (ii1=1; ii1<30; ii1+=4)
   {
     ps1  = sub(ps0, dn[2*ii1]);
     ps1a = sub(ps0a, dn[2*ii1+1]);

     /* alp1 = alp0*2 + rr[ii1][ii1] - 2.0*gain_i0*rr[ii0][ii1]  */
     /* The result is divided by 8 to avoid overflow.            */
     L_tmp = add_sh(alp0_32, rr[ii1][ii1], (Word16)13); 
     
     L_tmp = L_msu0(L_tmp, (Word16)Q14_gain_i0, rr[ii0][ii1]);
     alp1  = extract_h(L_tmp);
     alp1_32 = Load_sh(alp1, (Word16)15);

    /* If( abs( (ps1+ps1a)/2 ) > seuil1 */

     L_tmp = Load_sh(ps1, (Word16)15);
     L_tmp = L_abs( add_sh(L_tmp, ps1a, (Word16)15) );
     L_tmp = sub_sh16( L_tmp, seuil1);
     if( L_tmp > 0)
     {
       for (ii2=2; ii2<31; ii2+=4)
       {
         ps2  = add(ps1, dn[2*ii2]);
         ps2a = add(ps1a, dn[2*ii2+1]);

         /* alp2=alp1+rr[ii2][ii2]+2.0*(gain_i0*rr[ii0][ii2]-rr[ii1][ii2]) */
         /* The result is divided by 16 to avoid overflow.                 */

         L_tmp = add_sh(alp1_32, rr[ii2][ii2], (Word16)12);  
         
         L_tmp = L_mac0(L_tmp, (Word16)Q13_gain_i0, rr[ii0][ii2]);
         L_tmp = sub_sh(L_tmp, rr[ii1][ii2] , (Word16)13);
         alp2  = extract_h(L_tmp);
         alp2_32 = Load_sh16(alp2);
         
         /* If( abs( (ps2+ps2a)/2 ) > seuil2 */

         L_tmp = Load_sh(ps2, (Word16)15);
         L_tmp = L_abs( add_sh(L_tmp, ps2a, (Word16)15) );
         L_tmp = sub_sh16( L_tmp, seuil2);
         if( L_tmp > 0)
         {
           shif = 0;
           if( sub(abs_s(ps2a),abs_s(ps2)) > 0)
           {
             ps2  = ps2a;
             shif = 1;
           }

           ps2_32 = Load_sh(ps2, (Word16)15);
           
           for (ii3=3; ii3<32; ii3+=4)
           {
             /* ps3 = (ps2-dn[2*ii3+shift]) / 2                       */
             /* Need to work on 32 bits to avoid possible overflow */
             
             L_tmp = sub_sh(ps2_32, dn[2*ii3+shif], (Word16)15);

             ps3  = extract_h(L_tmp);

             /* alp3 = alp2 + rr[ii3][ii3] +                               */
             /*   2.0*(rr[ii1][ii3] - gain_i0*rr[ii0][ii3] - rr[ii2][ii3]) */
             /*                                                            */
             /* This part is the most critical part in all the coder       */

             L_tmp = add_sh(alp2_32, rr[ii3][ii3], (Word16)12);
             L_tmp = add_sh(L_tmp, rr[ii1][ii3], (Word16)13);
             L_tmp = L_msu0(L_tmp, (Word16)Q13_gain_i0, rr[ii0][ii3] );
             L_tmp = sub_sh(L_tmp, rr[ii2][ii3], (Word16)13);
             alp3  = extract_h(L_tmp);

             /* if( (ps3**2 * alpha) - (psc *alp3)  > 0 ) */
             /*    ->new maximum                          */

             ps3c = mult(ps3, ps3);
             L_tmp  = L_mult(ps3c, alpha);
             if( L_msu(L_tmp,psc,alp3) > 0)
             {
               ps    = ps3;
               psc   = ps3c;
               alpha = alp3;
               ip0 = 2*ii0;
               ip1 = 2*ii1;
               ip2 = 2*ii2;
               ip3 = 2*ii3;
               shift = shif;
             } /*  end of if(.. > 0) */
           } /* end of for ii3 = */

           time = sub(time, (Word16)3);	/* See note on complexity */
           if(time <= 0 ) goto fin;		/* Maximum time finish    */

         } /* end if >seuil2 */
       } /* end of for ii2 = */

       time = sub(time, (Word16)4);		/* See note on complexity */
       if(time <= 0 ) goto fin;		/* Maximum time finish    */

     } /* end if >seuil1 */
   } /* end of for ii1 = */
 } /* end of for ii0 = */

 fin:

 /* Convolve code with f[] */

 f -= shift;            /* Operations on pointers !!! */
 p0 = f - ip0;
 p1 = f - ip1;
 p2 = f - ip2;
 p3 = f - ip3;

 /* cod[i] = p0[i] * gain_i0  - p1[i] + p2[i] - p3[i]; */

 if(ps >= 0)
 {
   *sign = 0;
   for (i = 0; i < lcode; i++)
   {
     L_tmp  = L_mult0(p0[i], (Word16)Q11_gain_i0);
     L_tmp  = sub_sh(L_tmp, p1[i], (Word16)11);
     L_tmp  = add_sh(L_tmp, p2[i], (Word16)11);
     L_tmp  = sub_sh(L_tmp, p3[i], (Word16)11);
     cod[i] = store_hi(L_tmp, (Word16)5);
   }
 }
 else
 {
   *sign = 1;
   for (i = 0; i < lcode; i++)
   {
     L_tmp  = L_mult0(p0[i], (Word16)Q11_gain_i0);
     L_tmp  = sub_sh(L_tmp, p1[i], (Word16)11);
     L_tmp  = add_sh(L_tmp, p2[i], (Word16)11);
     L_tmp  = sub_sh(L_tmp, p3[i], (Word16)11);
     L_tmp  = L_negate(L_tmp);
     cod[i] = store_hi(L_tmp, (Word16)5);
   }
 }

 /* Convolve code with h[] */

 h -= shift;            /* Operations on pointers !!! */
 p0 = h - ip0;
 p1 = h - ip1;
 p2 = h - ip2;
 p3 = h - ip3;

 /* y[i] = p0[i] * gain_i0  - p1[i] + p2[i] - p3[i]; */

 if(ps >= 0)
 {
   for (i = 0; i < lcode; i++)
   {
     L_tmp = L_mult0(p0[i], (Word16)Q11_gain_i0);
     L_tmp = sub_sh(L_tmp, p1[i], (Word16)11);
     L_tmp = add_sh(L_tmp, p2[i], (Word16)11);
     L_tmp = sub_sh(L_tmp, p3[i], (Word16)11);
     y[i]  = store_hi(L_tmp, (Word16)5);
   }
 }
 else
 {
   for (i = 0; i < lcode; i++)
   {
     L_tmp = L_mult0(p0[i], (Word16)Q11_gain_i0);
     L_tmp = sub_sh(L_tmp, p1[i], (Word16)11);
     L_tmp = add_sh(L_tmp, p2[i], (Word16)11);
     L_tmp = sub_sh(L_tmp, p3[i], (Word16)11);
     L_tmp = L_negate(L_tmp);
     y[i]  = store_hi(L_tmp, (Word16)5);
   }
 }



 /* Return parameters */

 *shift_code = shift;

 /* index = (ip0>>1) + ( (ip1>>3)<<5 ) + ( (ip2>>3)<<8 ) + ( (ip3>>3)<<11 )*/

 index = shr(ip0, (Word16)1);
 index = add(index, shl( shr( ip1,(Word16)3 ),(Word16)5 ));
 index = add(index, shl( shr( ip2,(Word16)3 ),(Word16)8 ));
 index = add(index, shl( shr( ip3,(Word16)3 ),(Word16)11 ));

 return index;
}


/**************************************************************************
*
*	ROUTINE				:	D_D4i60
*
*	DESCRIPTION			:	Decode innovative codebook d4i60_16
*
**************************************************************************
*
*	USAGE				:	D_D4i60(index,sign, shift,buffer_in,buffer_out)
*							(Routine_Name(input1,input2,input3,input4,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Index of codebook
*						- Format : Word16
*
*	INPUT2			:	- Description : Sign of codebook
*						- Format : Word16
*
*	INPUT3			:	- Description : Shift of codebook
*						- Format : Word16
*
*	INPUT4			:	- Description : Noise filter
*						- Format : Word16 - (must be preceeded by 64 zeros)
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Innovative vector
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
*
**************************************************************************/

#define lcode 60

/* Gain for impulse 0 = sqrt(2) = 1.4142 = 2896 in Q11 */

#define Q11_gain_i0  2896

void D_D4i60(Word16 index, Word16 sign, Word16 shift, Word16 F[], Word16 cod[])
{
  Word16 i, pos0, pos1, pos2, pos3;
  Word16 *p0, *p1, *p2, *p3;
  Word32 L_tmp;

  /* Position of the 4 impulses */

  pos0 = shl( (Word16)(index & 31), (Word16)1);

  pos1 = shr( (Word16)(index & 224), (Word16)2);
  pos1 = add(pos1, (Word16)2);

  pos2 = shr( (Word16)(index & 1792), (Word16)5);
  pos2 = add(pos2, (Word16)4);

  pos3 = shr( (Word16)(index & 14336), (Word16)8);
  pos3 = add(pos3, (Word16)6);


  /* Convolve code with F[]                             */
  /* cod[i] = p0[i] * gain_i0  - p1[i] + p2[i] - p3[i]; */

  F -= shift;            /* Operations on pointers !!!  */
  p0 = F - pos0;
  p1 = F - pos1;
  p2 = F - pos2;
  p3 = F - pos3;

  if(sign == 0)
  {
    for (i = 0; i < lcode; i++)
    {
      L_tmp  = L_mult0(p0[i], (Word16)Q11_gain_i0);
      L_tmp  = sub_sh(L_tmp, p1[i], (Word16)11);
      L_tmp  = add_sh(L_tmp, p2[i], (Word16)11);
      L_tmp  = sub_sh(L_tmp, p3[i], (Word16)11);
      cod[i] = store_hi(L_tmp, (Word16)5);
    }
  }
  else
  {
    for (i = 0; i < lcode; i++)
    {
      L_tmp  = L_mult0(p0[i], (Word16)Q11_gain_i0);
      L_tmp  = sub_sh(L_tmp, p1[i], (Word16)11);
      L_tmp  = add_sh(L_tmp, p2[i], (Word16)11);
      L_tmp  = sub_sh(L_tmp, p3[i], (Word16)11);
      L_tmp  = L_negate(L_tmp);
      cod[i] = store_hi(L_tmp, (Word16)5);
    }
  }

  return;
}

/**************************************************************************
*
*	ROUTINE				:	D_Lsp334
*
*	DESCRIPTION			:	Decoding: Split vector quantization of 
*							LSP parameters
*
**************************************************************************
*
*	USAGE				:	D_Lsp334(buffer_in1,buffer_out1,buffer_in2)
*							(Routine_Name(input1,output1,input2))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : indices of the three selected 
*							          codebook entries
*						- Format : Word16
*
*		INPUT2			:	- Description : Previous LSP values
*								          (in the cosine domain)
*							- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Quantized LSPs (in the cosine domain)
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
*
**************************************************************************/

void D_Lsp334(Word16 indice[], Word16 lsp[], Word16 lsp_old[])
{
   Word16 i, *p, temp;

   p      = &dico1_clsp[ indice[0] * 3];
   lsp[0] = *p++ ;
   lsp[1] = *p++ ;
   lsp[2] = *p++ ;

   p      = &dico2_clsp[ indice[1] * 3];
   lsp[3] = *p++ ;
   lsp[4] = *p++ ;
   lsp[5] = *p++ ;

   p      = &dico3_clsp[ indice[2] * 4];
   lsp[6] = *p++ ;
   lsp[7] = *p++ ;
   lsp[8] = *p++ ;
   lsp[9] = *p++ ;

   /* Minimum distance between lsp[2] and lsp[3] */

   temp = 917;			/* 917 = 0.028 in Q15 = 50hz around 1000hz */
   temp = sub(temp, lsp[2]);
   temp = add(temp, lsp[3]);	/* temp = 0.028 - (lsp[2]-lsp[3])      */
   if (temp > 0)
   {
     temp = shr(temp, (Word16)1);
     lsp[2] = add(lsp[2], temp);
     lsp[3] = sub(lsp[3], temp);
   }


   /* Minimum distance between lsp[5] and lsp[6] */

   temp = 1245;			/* 1245= 0.038 in Q15 = 50hz around 1600hz */
   temp = sub(temp, lsp[5]);
   temp = add(temp, lsp[6]);	/* temp = 0.038 - (lsp[5]-lsp[6])      */
   if (temp > 0)
   {
     temp = shr( temp,(Word16)1 );
     lsp[5] = add(lsp[5], temp);
     lsp[6] = sub(lsp[6], temp);
   }

   /* Verify if lsp[] are still in order */

   temp = 0;
   for(i=0; i<9; i++)
   {
      if(sub(lsp[i],lsp[i+1]) <= 0 )
      {
        temp = 1;
      }
   }

  /* If lsp[] are not in order keep old lsp[] */

   if(temp != 0)
   {
     for(i=0; i<10; i++)
       lsp[i] = lsp_old[i];
   }
   return;
}


/**************************************************************************
*
*	ROUTINE				:	Ener_Qua
*
*	DESCRIPTION			:	Compute quantized gains of pitch and innovative
*						 	codebook resulting from the quantization of energies
*							of adaptive and innovation codebook
*
**************************************************************************
*
*	USAGE				:	Ener_Qua(buffer_in1,buffer_in2,buffer_in3,L_subfr,
*							gain_p,gain_c)
*							(Routine_Name(input1,input2,input3,input4,
*							arg5,arg6))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : LPC filter
*						- Format : Word16
*
*	INPUT2			:	- Description : Adaptive codebook
*						- Format : Word16
*
*	INPUT3			:	- Description : Innovation codebook
*						- Format : Word16
*
*	INPUT4			:	- Description : Subframe length
*						- Format : Word16
*
*		ARG5				:	- Description : Pitch gain
*							- Format : Word16
*	
*		ARG6				:	- Description : Code gain
*							- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		ARG5				:	- Description : Quantized pitch gain
*							- Format : Word16
*
*		ARG6				:	- Description : Quantized code gain
*							- Format : Word16
*
*	RETURNED VALUE		:	Index of quantization
*
**************************************************************************/

  extern Word16 last_ener_pit;
  extern Word16 last_ener_cod;

Word16 Ener_Qua(Word16 A[], Word16 prd_lt[], Word16 code[], Word16 L_subfr,
                Word16 *gain_pit, Word16 *gain_cod)
{

  Word16  i, j, index, tmp, *p;
  Word16  exp, frac;
  Word16  exp_lpc, ener_lpc;
  Word16  exp_plt, ener_plt, ener_pit, err_pit, pred_pit;
  Word16  ener_c, ener_cod, err_cod, pred_cod;
  Word32  L_tmp, dist, dist_min;


  /*------------------------------------------------------*
   * Energy of impulse response of 1/A(z) for length = 60 *
   *------------------------------------------------------*/

  L_tmp = Lpc_Gain(A);

  exp_lpc  = norm_l(L_tmp);
  ener_lpc = extract_h( L_shl(L_tmp, exp_lpc) );

  /*-------------------------------*
   * Energy coming from pitch      *
   *-------------------------------*/

  L_tmp = 1;            /* Avoid case of all-zeros */

  for(i=0; i<L_subfr; i++)
    L_tmp = L_mac0(L_tmp, prd_lt[i], prd_lt[i]);

  exp_plt  = norm_l(L_tmp);
  ener_plt = extract_h( L_shl(L_tmp, exp_plt) );

  /* ener_plt = Log2(ener_plt * ener_lpc) */

  L_tmp = L_mult0(ener_plt, ener_lpc);
  exp_plt = add(exp_plt, exp_lpc);

  Log2(L_tmp, &exp, &frac);

  L_tmp = Load_sh16(exp);
  L_tmp = add_sh(L_tmp, frac, (Word16)1);	/*Log2(ener_plt*ener_lpc) in Q16 */
  L_tmp = sub_sh16(L_tmp, exp_plt);		/* subtract exponant of ener_plt */

  /* Input on 15 bits */
  L_tmp = add_sh(L_tmp, (Word16)1710, (Word16)8);	/* +6.68 in Q16 
									for other scaling    */

  /* The scaling factor +6.68 includes many scalings, due to the fact that
     impulse response of the LP filter is in Q10 (see routine Lpc_Gain), and
     that the original quantization gain table was designed using -26 dB data
     reduced to 13 bits while the final coder works with -22dB signal reduced
     to 15 bits */

  L_tmp = L_shr(L_tmp, (Word16)8);		/* Convert from Q16 to Q8        */
  ener_plt = extract_l(L_tmp);

  /* ener_pit = Log2(gain_pit**2) + ener_plt */

  L_tmp = 1;					/* Avoid Log2(0) 			   */
  L_tmp = L_mac0(L_tmp, *gain_pit, *gain_pit);

  Log2(L_tmp, &exp, &frac);

  L_tmp = Load_sh16(exp);
  L_tmp = add_sh(L_tmp, frac, (Word16)1);	/* Log2(gain_pit**2)    in Q16   */
  L_tmp = sub_sh16(L_tmp, (Word16)24);	/* -24.0 -> gain_pit**2 is in Q24*/
 
  /* Pitch gain (variable "gain_pit")is in Q12, so its square is in Q24,
     which means that the real value is multplied by 2**24. Thus, in applying
     the function Log2(), a value of 24 is being added. A scaling factor of
     -24 is then needed to compensate  */

  L_tmp = L_shr(L_tmp, (Word16)8);		/* Convert from Q16 to Q8        */
  ener_pit = extract_l(L_tmp);
  ener_pit = add(ener_pit, ener_plt);


  /*-------------------------------*
   * Energy coming from code       *
   *-------------------------------*/

  L_tmp = 0;
  for(i=0; i<L_subfr; i++)
    L_tmp = L_mac0(L_tmp, code[i], code[i]);

  ener_c = extract_h(L_tmp);

  /* ener_c = Log2(ener_c * ener_lpc) */

  L_tmp = L_mult0(ener_c, ener_lpc);

  Log2(L_tmp, &exp, &frac);

  L_tmp = Load_sh16(exp);
  L_tmp = add_sh(L_tmp, frac, (Word16)1);	/* Log2(ener_plt*ener_lpc) in Q16*/
  L_tmp = sub_sh16(L_tmp, exp_lpc);		/* subtract exponant of ener_lpc */

  /* Input on 15 bits */
  L_tmp = sub_sh(L_tmp, (Word16)4434, (Word16)8);	/*-17.32 in Q16 
									for other scaling    */

  /* The vector "code[i]" is in Q12, so its square (variable "ener_c") is in
     Q24, which means that the real value is multplied by 2**24. Thus, in
     applying the function Log2(), a value of 24 is being added. A scaling
     factor of -24 is then needed to compensate, but as the other scaling
     factor of +6.68 (as explained above) has also to be applied, the final
     resulting factor is -17.32 */

  L_tmp = L_shr(L_tmp, (Word16)8);		/* Convert from Q16 to Q8        */
  ener_c = extract_l(L_tmp);

  /* ener_cod = Log2(gain_code**2) + ener_c */

  L_tmp = 1;					/* Avoid Log2(0) 			   */
  L_tmp = L_mac0(L_tmp, *gain_cod, *gain_cod);

  Log2(L_tmp, &exp, &frac);

  L_tmp = Load_sh16(exp);
  L_tmp = add_sh(L_tmp, frac, (Word16)1);	/* Log2(gain_code**2) in Q16	   */
  L_tmp = L_shr(L_tmp, (Word16)8);		/* Convert from Q16 to Q8        */
  ener_cod = extract_l(L_tmp);
  ener_cod = add(ener_cod, ener_c);

  /*-----------------------------------------------------------------*
   * Prediction on pitch energy and prediction error                 *
   *  pred_pit = 0.50 * last_ener_pit + 0.25 * last_ener_cod - 3.0   *
   *  if(pred_pit < 0.0) pred_pit = 0.0;                             *
   *  err_pit = ener_pit - pred_pit;                                 *
   *-----------------------------------------------------------------*/

  L_tmp = Load_sh(last_ener_pit, (Word16)8); /* .5 last_ener_pit in Q9     */
  L_tmp = add_sh(L_tmp, last_ener_cod, (Word16)7); /*+.25 last_ener_code 
											in Q9    */
  L_tmp = sub_sh(L_tmp, (Word16)768, (Word16)9); /* -3.0 in Q9             */
  if(L_tmp < 0) L_tmp = 0;
  pred_pit = store_hi(L_tmp, (Word16)7);	/* result in Q8 			   */
  err_pit  = sub(ener_pit, pred_pit);


  /*-----------------------------------------------------------------*
   * Prediction on code energy and prediction error                  *
   *  pred_cod = 0.50 * last_ener_cod + 0.25 * last_ener_pit - 3.0   *
   *  if(pred_cod < 0.0) pred_cod = 0.0;                             *
   *  err_cod = ener_cod - pred_cod;                                 *
   *-----------------------------------------------------------------*/

  L_tmp = Load_sh(last_ener_cod, (Word16)8); /* .5 last_ener_cod  in Q9    */
  L_tmp = add_sh(L_tmp, last_ener_pit, (Word16)7); /*+.25 last_ener_pit
											in Q9    */
  L_tmp = sub_sh(L_tmp, (Word16)768, (Word16)9); /* -3.0 in Q9             */
  if(L_tmp < 0) L_tmp = 0;
  pred_cod = store_hi(L_tmp, (Word16)7);	/* result in Q8 			   */
  err_cod  = sub(ener_cod, pred_cod);


  /*-----------------------------------------------------------------*
   * Codebook search.                                                *
   * Find vector which minimizes:                                    *
   *                                                                 *
   *   Min k :  (err_pit - dico[0,k])**2 +  (err_cod - dico[1,k])**2 *
   *                                                                 *
   *-----------------------------------------------------------------*/

  dist_min = MAX_32;
  p = t_qua_ener;

  for (i = 0; i< nb_qua_ener; i++)
  {
     tmp  = sub(*p++, err_pit);
     dist = L_mult0(tmp, tmp);
     tmp  = sub(*p++, err_cod);
     dist = L_mac0(dist, tmp, tmp);



     if (L_sub(dist, dist_min) < 0) { dist_min = dist; index = i; }
  }

  j = shl(index, (Word16)1);
  last_ener_pit = add(t_qua_ener[j],   pred_pit);
  last_ener_cod = add(t_qua_ener[j+1], pred_cod);

  /* Limit energies ->for transmission errors */

  if(sub(last_ener_pit, (Word16)6912) > 0) last_ener_pit = 6912;
									/* 6912 = 27 in Q8 */
  if(sub(last_ener_cod, (Word16)6400) > 0) last_ener_cod = 6400;
									/* 6400 = 25 in Q8 */

  /*---------------------------------------------------*
   *                                                   *
   *  Compute the quantized pitch gain.                *
   *                                                   *
   *     temp = 0.5 * ( last_ener_pit - ener_plt );    *
   *     temp = pow(2.0, temp);                        *
   *     if( temp > 1.2) temp = 1.2;                   *
   *     *gain_pit = temp;                             *
   *                                                   *
   *---------------------------------------------------*/

  L_tmp = Load_sh(last_ener_pit, (Word16)6);	/* last_ener_pit/2 in Q15 */
  L_tmp = sub_sh(L_tmp, ener_plt, (Word16)6);	/* - ener_plt/2    in Q15 */
  L_tmp = add_sh(L_tmp, (Word16)12, (Word16)15); /* to have gain in Q12   */
  L_extract(L_tmp, &exp, &frac);
  L_tmp = pow2(exp, frac);
  if( L_sub(L_tmp, (Word32)4915) > 0) L_tmp = 4915; /* 4915 = 1.2 in Q12  */
  *gain_pit = extract_l(L_tmp);


  /*---------------------------------------------------*
   *                                                   *
   *  Compute the innovative code gain.                *
   *                                                   *
   *     temp = 0.5 * ( last_ener_cod - ener_c );      *
   *     *gain_cod = pow(2.0, temp);                   *
   *                                                   *
   *---------------------------------------------------*/

  L_tmp = Load_sh(last_ener_cod, (Word16)6);	/* last_ener_cod/2 in Q15 */
  L_tmp = sub_sh(L_tmp, ener_c, (Word16)6);	/* - ener_c/2      in Q15 */
  L_extract(L_tmp, &exp, &frac);
  L_tmp = pow2(exp, frac);
  *gain_cod = extract_l(L_tmp);

  return index;
}


/**************************************************************************
*
*	ROUTINE				:	G_Code
*
*	DESCRIPTION			:	Compute the gain of innovative code
*
**************************************************************************
*
*	USAGE				:	G_Code(buffer_in1,buffer_in2,L_subfr)
*							(Routine_Name(input1,input2,input3))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Code target
*						- Format : Word16
*
*		INPUT2			:	- Description : Filtered innovation code (with sign)
*							- Format : Word16
*
*	INPUT3			:	- Description : Length of subframe
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	None
*
*	RETURNED VALUE		:	Gain of innovation code
*
**************************************************************************/

Word16 G_Code(Word16 xn2[], Word16 y2[], Word16 L_subfr)
{
   Word16 i;
   Word16 xy, yy, exp_xy, exp_yy, gain;
   Word32 s, L_tmp;

   Overflow = 0;

/* Compute scalar product <xn2[],y2[]> */

   s = 1;					/* Avoid case of all zeros */
   for(i=0; i<L_subfr; i++)
     s = L_mac0(s, xn2[i], y2[i]);

   exp_xy = norm_l(s);
   xy     = extract_h( L_shl(s, exp_xy) );

/* Compute scalar product <y2[],y2[]> */

   s = 1;					/* Avoid case of all zeros */
   for(i=0; i<L_subfr; i++)
     s = L_mac0(s, y2[i], y2[i]);

   exp_yy = norm_l(s);
   yy     = extract_h( L_shl(s, exp_yy) );


/* Test if Overflow */

   if(Overflow == 1)
   {
      /* Compute scalar product <xn2[],y2[]> */

      s = 1;				/* Avoid case of all zeros */
      for(i=0; i<L_subfr; i++)
      {
        L_tmp = L_mult0(xn2[i], y2[i]);
	L_tmp = L_shr(L_tmp, (Word16)6);
        s = L_add(s, L_tmp);
      }

      exp_xy = norm_l(s);
      xy     = extract_h( L_shl(s, exp_xy) );

      /* Compute scalar product <y2[],y2[]> */

      s = 1;				/* Avoid case of all zeros */
      for(i=0; i<L_subfr; i++)
      {
        L_tmp = L_mult0(y2[i], y2[i]);
	L_tmp = L_shr(L_tmp, (Word16)6);
        s = L_add(s, L_tmp);
      }

      exp_yy = norm_l(s);
      yy     = extract_h( L_shl(s, exp_yy) );

   }

/* If (xy < 0) gain = 0  */

   if( xy <= 0) return( (Word16) 0);

/* compute gain = xy/yy */

   xy = shr(xy, (Word16)1);			/* Be sure xy < yy */
   gain = div_s( xy, yy);

   i = add(exp_xy, (Word16)2);		/* Denormalization of division */
   i = sub(i, exp_yy);

   gain = shr(gain, i);

   return(gain);
}


/**************************************************************************
*
*	ROUTINE				:	G_Pitch
*
*	DESCRIPTION			:	Compute the gain of pitch. Result in Q12
*							if (gain < 0)  gain =0
*								if (gain >1.2) gain =1.2
*
**************************************************************************
*
*	USAGE				:	G_Pitch(buffer_in1,buffer_in2,L_subfr)
*							(Routine_Name(input1,input2,input3))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Pitch target
*						- Format : Word16
*
*		INPUT2			:	- Description : Filtered adaptive codebook
*							- Format : Word16
*
*	INPUT3			:	- Description : Length of subframe
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	None
*
*	RETURNED VALUE		:	Gain of pitch lag in Q12 saturated to 1.2
*
**************************************************************************/

Word16 G_Pitch(Word16 xn[], Word16 y1[], Word16 L_subfr)
{
   Word16 i;
   Word16 xy, yy, exp_xy, exp_yy, gain;
   Word32 s, L_tmp;

   Overflow = 0;

/* Compute scalar product <xn[],y1[]> */

   s = 1;					/* Avoid case of all zeros */
   for(i=0; i<L_subfr; i++)
     s = L_mac0(s, xn[i], y1[i]);

   exp_xy = norm_l(s);
   xy     = extract_h( L_shl(s, exp_xy) );

/* Compute scalar product <y1[],y1[]> */

   s = 1;					/* Avoid case of all zeros */
   for(i=0; i<L_subfr; i++)
     s = L_mac0(s, y1[i], y1[i]);

   exp_yy = norm_l(s);
   yy     = extract_h( L_shl(s, exp_yy) );


/* Test if Overflow */

   if(Overflow != 0)
   {
     /* Compute scalar product <xn[],y1[]> */

      s = 1;				/* Avoid case of all zeros */
      for(i=0; i<L_subfr; i++)
      {
        L_tmp = L_mult0(xn[i], y1[i]);
        L_tmp = L_shr(L_tmp, (Word16)6);
        s = L_add(s, L_tmp);
      }

      exp_xy = norm_l(s);
      xy     = extract_h( L_shl(s, exp_xy) );

      /* Compute scalar product <y1[],y1[]> */

      s = 1;				/* Avoid case of all zeros */
      for(i=0; i<L_subfr; i++)
      {
        L_tmp = L_mult0(y1[i], y1[i]);
        L_tmp = L_shr(L_tmp, (Word16)6);
        s = L_add(s, L_tmp);
      }

      exp_yy = norm_l(s);
      yy     = extract_h( L_shl(s, exp_yy) );

   }

/* If (xy < 4) gain = 0 */

   if( sub(xy, (Word16)4) < 0) return( (Word16) 0);

/* compute gain = xy/yy */

   xy = shr(xy, (Word16)1);			/* Be sure xy < yy */
   gain = div_s( xy, yy);

   i = add(exp_xy, (Word16)2);		/* Denormalization of division */
   i = sub(i, exp_yy);

   gain = shr(gain, i);

/* if(gain >1.2) gain = 1.2  in Q12 */

   if( sub(gain, (Word16)4915) > 0) gain = 4915;

   return(gain);
}


/**************************************************************************
*
*	ROUTINE				:	Inter8_M1_3
*
*	DESCRIPTION			:	Fractional interpolation -1/3 with 8 coefficients
*
**************************************************************************
*
*	USAGE				:	Inter8_M1_3(buffer_in)
*							(Routine_Name(input1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : Buffer containing the function
*								          to be interpolated 
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	None
*
*	RETURNED VALUE		:	- Description : Interpolated value 
*						- Format : Word32
*
**************************************************************************/

Word32 Inter8_M1_3(Word16 x[])
{
  Word16 i;
  Word32 s;
  static Word16 coef[8] = {-236,1050,-3572,12714,26674,-5217,1630,-384};

  s = 0;
  for(i=0; i<8; i++)
    s = L_mac0(s, x[i-4], coef[i]);

  return(s);
}


/**************************************************************************
*
*	ROUTINE				:	Inter8_1_3
*
*	DESCRIPTION			:	Fractional interpolation 1/3 with 8 coefficients
*
**************************************************************************
*
*	USAGE				:	Inter8_1_3(buffer_in)
*							(Routine_Name(input1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : Buffer containing the function
*								          to be interpolated 
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	None
*
*	RETURNED VALUE		:	- Description : Interpolated value 
*						- Format : Word32
*
**************************************************************************/

Word32 Inter8_1_3(Word16 x[])
{
  Word16 i;
  Word32 s;
  static Word16 coef[8] = {-384,1630,-5217,26674,12714,-3572,1050,-236};

  s = 0;
  for(i=0; i<8; i++)
    s = L_mac0(s, x[i-3], coef[i]);

  return(s);
}


/**************************************************************************
*
*	ROUTINE				:	Inter32_M1_3
*
*	DESCRIPTION			:	Fractional interpolation -1/3 with 32 coefficients
*
**************************************************************************
*
*	USAGE				:	Inter32_M1_3(buffer_in)
*							(Routine_Name(input1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : Buffer containing the function
*								          to be interpolated 
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	None
*
*	RETURNED VALUE		:	- Description : Interpolated value 
*						- Format : Word16
*
*	COMMENTS			:	For long term prediction, it must be noted that
*							exc[-(T0-1/3)] corresponds to exc[-T0+1/3]
*
**************************************************************************/

Word16 Inter32_M1_3(Word16 x[])
{
  Word16 i;
  Word32 s;

  static Word16 coef[32] = {
              -49,    66,   -96,   142,  -207,   294,  -407,   553,  -739,
       981, -1304,  1758, -2452,  3688, -6669, 27072, 13496, -5287,  3179,
     -2182,  1587, -1185,   893,  -672,   500,  -366,   263,  -183,   125,
       -84,    59,   -47 };

  s = 0;
  for(i=0; i<32; i++)
    s = L_mac0(s, x[i-15], coef[i]);

  s = L_add(s, s);
  i = round(s);
  return(i);
}


/**************************************************************************
*
*	ROUTINE				:	Inter32_1_3
*
*	DESCRIPTION			:	Fractional interpolation 1/3 with 32 coefficients
*
**************************************************************************
*
*	USAGE				:	Inter32_1_3(buffer_in)
*							(Routine_Name(input1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : Buffer containing the function
*								          to be interpolated 
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	None
*
*	RETURNED VALUE		:	- Description : Interpolated value 
*						- Format : Word16
*
*	COMMENTS			:	For long term prediction, it must be noted that
*							exc[-(T0+1/3)] corresponds to exc[-T0-1/3]
*
**************************************************************************/

Word16 Inter32_1_3(Word16 x[])
{
  Word16 i;
  Word32 s;

  static Word16 coef[32] = {
      -47,    59,   -84,   125,  -183,   263,  -366,   500,  -672,   893,
    -1185,  1587, -2182,  3179, -5287, 13496, 27072, -6669,  3688, -2452,
     1758, -1304,   981,  -739,   553,  -407,   294,  -207,   142,   -96,
       66,   -49};

  s = 0;
  for(i=0; i<32; i++)
    s = L_mac0(s, x[i-16], coef[i]);

  s = L_add(s, s);
  i = round(s);
  return(i);
}


/**************************************************************************
*
*	ROUTINE				:	Lag_Max
*
*	DESCRIPTION			:	Find the lag that has maximum correlation with
*							the input buffer sig_dec[]
*
**************************************************************************
*
*	USAGE				:	Lag_Max(buffer_in1,buffer_in2,
*							L_frame, lag_max,lag_min,cor_max)
*							(Routine_Name(input1,input2,
*							input3,input4,input5,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description :	- Signal used to compute 
*								the open loop pitch
*								- Buffer_in1[-142] to buffer_in1[-1] 
*								should be known
*						- Format : Word16
*
*	INPUT2			:	- Description : Decimated signal (buffer sig_dec[])
*						- Format : Word16
*
*	INPUT3			:	- Description : Length of frame to compute pitch
*						- Format : Word16
*
*	INPUT4			:	- Description : Maximum lag
*						- Format : Word16
*
*		INPUT5			:	- Description : Minimum lag
*							- Format : Word16
*	
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Maximum of normalized correlation 
*								         of lag found
*							- Format : Word16
*
*	RETURNED VALUE		:	- Description : Lag found
*							- Format : Word16
*
**************************************************************************/

Word16 Lag_Max(Word16 signal[], Word16 sig_dec[], Word16 L_frame,
               Word16 lag_max, Word16 lag_min, Word16 *cor_max)
{
  Word16  i, j;
  Word16  *p, *p1;
  Word32  max, t0;
  Word16  max_h, max_l, ener_h, ener_l;
  Word16  p_max;

  max = MIN_32;


  for (i = lag_max; i >= lag_min; i--)
  {
    p  = sig_dec;
    p1 = &signal[-i];
    t0 = 0;

    for (j=0; j<L_frame; j+=2, p++, p1+=2)
      t0 = L_mac0(t0, *p, *p1);

    if (L_sub(t0,max) >= 0)
    {
      max    = t0;
      p_max = i;
    }
  }

  max = L_shr(max, (Word16)1);	/* for special double precision format */
  L_extract(max, &max_h, &max_l);

  /* compute energie */

  t0 = 0;
  p = &signal[-p_max];
  for(i=0; i<L_frame; i+=2, p+=2)
    t0 = L_mac0(t0, *p, *p);

  /* 1/sqrt(energie),    result in Q30 */

  t0 = inv_sqrt(t0);
  L_extract(t0, &ener_h, &ener_l);

  /* max = max/sqrt(energie)                  */
  /* This result will always be on 16 bits !! */

  t0 = mpy_32(max_h, max_l, ener_h, ener_l);
  *cor_max = extract_l(t0);

  return(p_max);
}


/**************************************************************************
*
*	ROUTINE				:	Norm_Corr
*
*	DESCRIPTION			:	Find the normalized correlation 
*						(correlation between the target vector and 
*						the filtered past excitation divided by the square root
*							of  energy of filtered excitation) 
*
**************************************************************************
*
*	USAGE				:	Norm_Corr(buffer_in1,buffer_in2,buffer_in3,
*							L_subfr,t_min,t_max,corr_norm)
*							(Routine_Name(input1,input2,input3,
*							input4,input5,input6,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Excitation buffer
*						- Format : Word16
*
*	INPUT2			:	- Description : Target vector
*						- Format : Word16
*
*	INPUT3			:	- Description : Impulse response of synthesis 
*							          and weighting filters
*						- Format : Word16 - Q12
*
*	INPUT4			:	- Description : Length of subframe
*						- Format : Word16
*
*		INPUT5			:	- Description : Minimum value of pitch lag
*							- Format : Word16
*
*		INPUT6			:	- Description : Maximum value of pitch lag
*							- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Normalized correlation
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Norm_Corr(Word16 exc[], Word16 xn[], Word16 h[], Word16 L_subfr,
               Word16 t_min, Word16 t_max, Word16 corr_norm[])
{
 Word16 i,j,k;
 Word16 corr_h, corr_l, norm_hi, norm_lo;
 Word32 s;
 Word16 excf[80];			/* Usally dynamic allocation of (L_subfr) */



 k = - t_min;

 /* compute the filtered excitation for the first delay t_min */

 Convolve(&exc[k], h, excf, L_subfr);

 /* loop for every possible period */

 for (i = t_min; i <= t_max; ++i)
 {

   /* Compute correlation between xn[] and excf[] */

   s = 0;
   for (j = 0; j < L_subfr; j++)
     s = L_mac0(s, xn[j], excf[j]);

   s = L_shr(s, (Word16)1);		/* Special double precision format */
   L_extract(s, &corr_h, &corr_l);


   /* Compute 1/sqrt(energie of excf[]) */

   s = 0;
   for (j = 0; j < L_subfr; j++)
     s = L_mac0(s, excf[j], excf[j]);

   s = inv_sqrt(s);			/* Result in Q30 */
   L_extract(s, &norm_hi, &norm_lo);


   /* Normalize correlation = correlation * (1/sqrt(energie)) */

   s = mpy_32(corr_h, corr_l, norm_hi, norm_lo);

   corr_norm[i] = extract_l(s);	/* Result is on 16 bits */


   /* modify the filtered excitation excf[] for the next iteration */

   if( sub(i, t_max) != 0)
   {
     k--;
     for (j = L_subfr-1; j > 0; j--)
     {
        s = L_mult0(exc[k], h[j]);
        s = add_sh(s, excf[j-1], (Word16)12);
        excf[j] = store_hi(s, (Word16)4);
     }
      excf[0] = exc[k];
   }
 }
 return;
}


/**************************************************************************
*
*	ROUTINE				:	Pitch_Fr
*
*	DESCRIPTION			:	Find the pitch period with 1/3 subsample resolution
*
**************************************************************************
*
*	USAGE				:	Pitch_Fr(buffer_in1,buffer_in2,buffer_in3,
*							L_subfr,t0_min,t0_max,i_subfr,pit_frac)
*							(Routine_Name(input1,input2,input3,
*							input4,input5,input6,input7,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description : Excitation buffer
*						- Format : Word16
*
*	INPUT2			:	- Description : Target vector
*						- Format : Word16
*
*	INPUT3			:	- Description : Impulse response of synthesis 
*							          and weighting filters
*						- Format : Word16 - Q12
*
*	INPUT4			:	- Description : Length of subframe
*						- Format : Word16
*
*		INPUT5			:	- Description : Minimum value in the searched range
*							- Format : Word16
*
*		INPUT6			:	- Description : Maximum value in the searched range
*							- Format : Word16
*
*		INPUT7			:	- Description : Indicator for first subframe
*							- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Chosen fraction : (-1, 0, 1) / 3
*							- Format : Word16
*
*	RETURNED VALUE		:	- Description : Pitch period
*							- Format : Word16
*
**************************************************************************/

       /* Lg_inter = Length for fractionnal interpolation = nb.coeff/2 */
#define Lg_inter 4

Word16 Pitch_Fr(Word16 exc[], Word16 xn[], Word16 h[], Word16 L_subfr,
                Word16 t0_min, Word16 t0_max, Word16 i_subfr, 
                Word16 *pit_frac)
{
  Word16 i;
  Word16 t_min, t_max;
  Word16 max, lag, frac;
  Word16 *corr;
  Word32 corr_int, L_max;
  Word16 corr_v[40];	/* Total length = t0_max-t0_min+1+2*Lg_inter */

  /* Find interval to compute normalized correlation */

  t_min = sub(t0_min, (Word16)Lg_inter);
  t_max = add(t0_max, (Word16)Lg_inter);

  corr = &corr_v[-t_min];

  /* Compute normalized correlation between target and filtered excitation */

  Norm_Corr(exc, xn, h, L_subfr, t_min, t_max, corr);

  /* Find integer pitch */

  max = corr[t0_min];
  lag = t0_min;

  for(i= t0_min+1; i<=t0_max; i++)
  {
    if( sub(corr[i],max)>= 0)
    {
      max = corr[i];
      lag = i;
    }
  }
  /* If first subframe and lag > 84 do not search fractionnal pitch */

  if( (i_subfr == 0) && (sub(lag, (Word16)84) > 0) )
  {
    *pit_frac = 0;
    return(lag);
  }

  /* Test the fractions around T0 and choose the one which maximizes   */
  /* the interpolated normalized correlation.                          */

  frac  = 0;
  L_max = Load_sh(max, (Word16)15);

  /* test +1/3 */

  corr_int = Inter8_1_3(&corr[lag]);
  if(L_sub(corr_int, L_max) >= 0)
    { L_max=corr_int; frac= 1;}

  /* test +2/3  = 1-1/3 */

  corr_int = Inter8_M1_3(&corr[lag+1]);
  if(L_sub(corr_int, L_max) >= 0)
    { L_max=corr_int; frac= 2;}

  /* test -2/3 = 1/3 -1 */

  corr_int = Inter8_1_3(&corr[lag-1]);
  if(L_sub(corr_int, L_max) >= 0)
    { L_max=corr_int; frac= -2;}

  /* test -1/3 */

  corr_int = Inter8_M1_3(&corr[lag]);
  if(L_sub(corr_int, L_max) >= 0)
    { L_max=corr_int; frac= -1;}

  if(sub(frac, (Word16)2) == 0)
    { frac = -1; lag = add(lag, (Word16)1);};
  if(sub(frac, (Word16)-2) == 0)
    { frac = 1; lag = sub(lag, (Word16)1);};
  *pit_frac = frac;
  return(lag);
}

/**************************************************************************
*
*	ROUTINE				:	Pitch_Ol_Dec
*
*	DESCRIPTION			:	Compute the open loop pitch lag
*							(includes decimation of signal)
*
**************************************************************************
*
*	USAGE				:	Pitch_Ol_Dec(buffer_in,L_frame)
*							(Routine_Name(input1,input2))
*
*	INPUT ARGUMENT(S)		:	
*
*	INPUT1			:	- Description :	- Signal used to compute 
*								the open loop pitch
*								- Buffer_in[-142] to buffer_in[-1] 
*								should be known
*						- Format : Word16
*
*	INPUT2			:	- Description : Length of frame to compute pitch
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	None
*
*	RETURNED VALUE		:	- Description : Open pitch lag as found
*							- Format : Word16
*
**************************************************************************/

/* Minimum and maximum pitch lag */

#define pit_min 20
#define pit_max 142

/* Threshold to favor small pitch = 0.85 in Q15 */

#define seuil 27856

Word16 Pitch_Ol_Dec(Word16 signal[], Word16 L_frame)
{
  Word16  i, j;
  Word16  max1, max2, max3;
  Word16  p_max1, p_max2, p_max3;
  Word32  t0;

  /* Decimated signal                                       */
  /* Can be allocated with memory allocation of(L_frame/2)  */

  Word16  sig_dec[120];


  /*--------------------------------------------------------*
   *  Verification for risk of overflow.                    *
   *--------------------------------------------------------*/

   Overflow = 0;
   t0 = 0;
   for(i= -pit_max; i< L_frame; i+=2)
     t0 = L_mac0(t0, signal[i], signal[i]);



  /*--------------------------------------------------------*
   * Decimation of signal and scaling.                      *
   *                                                        *
   *   if Overflow        -> sig_dec[i] = signal[i*2]>>6    *
   *   else if t0 < 1<<22 -> sig_dec[i] = signal[i*2]<<4    *
   *   else               -> sig_dec[i] = signal[i*2]       *
   *--------------------------------------------------------*/

   if(Overflow == 1)
   {
     for(i=0, j=0; i<L_frame; i+=2, j++)
       sig_dec[j] = shr(signal[i], (Word16)6);
   }
   else if (L_sub(t0, L_shl( (Word32)1, (Word16)22)) < 0 )
   {
     for(i=0, j=0; i<L_frame; i+=2, j++)
       sig_dec[j] = shl(signal[i], (Word16)4);
   }
   else
   {
     for(i=0, j=0; i<L_frame; i+=2, j++)
       sig_dec[j] = signal[i];
   }

  /*--------------------------------------------------------------------*
   *  The pitch lag search is divided in three sections.                *
   *  Each section cannot have a pitch multiple.                        *
   *  A maximum is found for each section.                              *
   *  The maximum of each section is compared to favor small lag.       *
   *                                                                    *
   *  First section:  lag delay = pit_max to 80                         *
   *  Second section: lag delay = 79 to 40                              *
   *  Third section:  lag delay = 39 to 20                              *
   *--------------------------------------------------------------------*/

   p_max1 = Lag_Max(signal, sig_dec, L_frame, (Word16)pit_max,
									(Word16)80 , &max1);
   p_max2 = Lag_Max(signal, sig_dec, L_frame, (Word16)79     ,
									(Word16)40 , &max2);
   p_max3 = Lag_Max(signal, sig_dec, L_frame, (Word16)39     ,
									(Word16)20 , &max3);

  /*--------------------------------------------------------------------*
   * Compare the 3 sections maximum, and favor small lag.               *
   *--------------------------------------------------------------------*/

  if( sub(mult((Word16)max1, (Word16)seuil), (Word16)max2)  < 0)
    { max1 = max2;  p_max1 = p_max2;}

  if( sub(mult((Word16)max1, (Word16)seuil), (Word16)max3)  < 0)
    p_max1 = p_max3;


  return (p_max1);
}


/**************************************************************************
*
*	ROUTINE				:	Post_Process
*
*	DESCRIPTION			:	Post-processing of output speech
*							Multiplication by two of output speech
*							with saturation
*
**************************************************************************
*
*	USAGE				:	Post_Process(buffer,Length)
*							(Routine_Name(arg1,input2))
*
*	INPUT ARGUMENT(S)		:	
*
*	ARG1				:	- Description : Input speech signal buffer
*						- Format : Word16
*
*		INPUT2			:	- Description : Length of signal
*							- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		ARG1				:	- Description : Output speech signal buffer
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Post_Process(Word16 signal[], Word16 lg)
{
  Word16 i;

  for(i=0; i<lg; i++)
    signal[i] = add(signal[i], signal[i]);
}


/**************************************************************************
*
*	ROUTINE				:	Pred_Lt
*
*	DESCRIPTION			:	Compute the result of long term prediction with
*							fractional interpolation
*
**************************************************************************
*
*	USAGE				:	Pred_Lt(buffer,T0,frac,L_subfr)
*							(Routine_Name(arg1,input2,input3,input4))
*
*	INPUT ARGUMENT(S)		:	
*
*	ARG1				:	- Description : Excitation vector
*						- Format : Word16
*
*	INPUT2			:	- Description : Pitch lag
*						- Format : Word16
*
*	INPUT3			:	- Description : Fraction of pitch lag : (-1, 0, 1)  / 3
*						- Format : Word16 - Q12
*
*	INPUT4			:	- Description : Length of subframe
*						- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		ARG1				:	- Description : Interpolated signal contained in
*								         buffer[0..L_subfr-1]
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Pred_Lt(Word16 exc[], Word16 T0, Word16 frac, Word16 L_subfr)
{
   Word16 i;

   if(frac == 0)
   {
      for (i = 0; i < L_subfr; i++)
         exc[i] = exc[i-T0];
   }
   else if( sub(frac, (Word16)1) == 0)
   {
      for (i = 0; i < L_subfr; i++)
         exc[i] = Inter32_1_3(&exc[i-T0]);
   }
   else if( sub(frac, (Word16)-1) == 0)
   {
      for (i = 0; i < L_subfr; i++)
         exc[i] = Inter32_M1_3(&exc[i-T0]);
   }

   return;
}


/**************************************************************************
*
*	ROUTINE				:	Pre_Process
*							(include Init_Pre_Process)
*
*	DESCRIPTION			:	Preprocessing of input speech
*							- Offset compensation
*								- Divide input by two
*
**************************************************************************
*
*	USAGE				:	Pre_Process(buffer,Length)
*							(Routine_Name(arg1,input2))
*
*	INPUT ARGUMENT(S)		:	
*
*	ARG1				:	- Description : Input speech signal buffer
*						- Format : Word16
*
*		INPUT2			:	- Description : Length of signal
*							- Format : Word16
*
*	OUTPUT ARGUMENT(S)		:	
*
*		ARG1				:	- Description : Output speech signal buffer
*							- Format : Word16
*
*	RETURNED VALUE		:	None
*
*	COMMENTS			:	Algorithm :
*
*						y[i] = x[i]/2 - x[i-1]/2 + alpha * y[i-1]
*
*  						alpha = 32735 / 2**15
*  						y[i-1] is keep in double precision
*
*  						It is the same algorithm than in GSM except that :
*  						- Input is divided by two in the filtering process
*  						- No rounding
*
**************************************************************************/

/* Static values to be preserved between calls */

static Word16 y_hi, y_lo, x0;

/* Initialization of static values */

void Init_Pre_Process(void)
{
  y_hi = 0;
  y_lo = 0;
  x0   = 0;
}


/* Offset compensation and divide by 2 */

void Pre_Process(Word16 signal[], Word16 lg)
{
  Word16 i, x1;
  Word32 L_tmp;

  for(i=0; i<lg; i++)
  {
     x1 = x0;
     x0 = signal[i];

     L_tmp     = Load_sh(x0, (Word16)15);
     L_tmp     = sub_sh(L_tmp, x1, (Word16)15);
     L_tmp     = L_mac(L_tmp, y_hi, (Word16)32735);
     L_tmp     = add_sh(L_tmp, mult(y_lo, (Word16)32735), (Word16)1);
     signal[i] = extract_h(L_tmp);
     y_hi      = extract_h(L_tmp);
     y_lo      = extract_l(sub_sh(L_shr( L_tmp,(Word16)1 ), y_hi, (Word16)15));
  }
  return;
}

/**************************************************************************
*
*	ROUTINE				:	Prm2bits_Tetra
*
*	DESCRIPTION			:	Convert the encoder parameter vector into 
*							a vector of serial bits
*
**************************************************************************
*
*	USAGE				:	Prm2bits_Tetra(buffer_in,buffer_out)
*							(Routine_Name(input1,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : Encoded parameters  
*								         (23 parameters)
*							- Format : Word16 - .. * 16 bit-samples
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Serial bits (137 + bfi)
*							- Format : Word16 - .. * 16 bit-samples
*
*	RETURNED VALUE		:	None
*
*	COMMENTS			:	The transmitted parameters are :
*
*						- LSP	1st codebook 			8 bits
*							2nd codebook			9 bits
*							3nd codebook			9 bits
*
*						- for the 4 subframes :
*							pitch delay			8 bits (first)
*											5 bits (others)
*							codebook index		14 bits
*							pulse global sign		1 bit
*							pulse shift			1 bit
*							pitch and innovation gains	6 bits
*
**************************************************************************/

#define PRM_NO    23

void Prm2bits_Tetra(Word16 prm[], Word16 bits[])
{
  Word16 i;
  static Word16 bitno[PRM_NO] = {8, 9, 9,            /* split VQ LSP  */
                                 8, 14, 1, 1, 6,     /* subframe 1    */
                                 5, 14, 1, 1, 6,     /* subframe 2    */
                                 5, 14, 1, 1, 6,     /* subframe 3    */
                                 5, 14, 1, 1, 6};    /* subframe 4    */

  *bits++ = 0;	/* bit[0] = 0, at receiver this bits indicate BFI */

  for (i = 0; i < PRM_NO; i++)
  {
    int2bin(prm[i], bitno[i], bits);
    bits += bitno[i];
  }
  return;
}

