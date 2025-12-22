/************************************************************************
*
*	FILENAME		:	source.h
*
*	DESCRIPTION		:	DEFINITIONS
*
*					FUNCTION PROTOTYPES for the TETRA
*					speech source coder and decoder
*
*					OPERATOR PROTOTYPES for TETRA codec
*
************************************************************************/

/************************************************************************
*
*      DEFINITIONS
*
************************************************************************/

#ifndef TYPEDEF_H
#define TYPEDEF_H


typedef short Word16;
typedef long  Word32;
typedef int   Flag;

#endif


/************************************************************************
*
*	DESCRIPTION		:	FUNCTION PROTOTYPES for the TETRA
*					speech source coder and decoder
*
************************************************************************/

#ifndef TETRA_H
#define TETRA_H


/* Basic functions */

Word32 add_sh(Word32 L_var, Word16 var1, Word16 shift);
Word32 add_sh16(Word32 L_var, Word16 var1);
Word16 bin2int(Word16 no_of_bits, Word16 *bitstream);
void   int2bin(Word16 value, Word16 no_of_bits, Word16 *bitstream);
Word32 Load_sh(Word16 var1, Word16 shift);
Word32 Load_sh16(Word16 var1);
Word32 norm_v(Word32 L_var3, Word16 var1, Word16 *var2);
Word16 store_hi(Word32 L_var1, Word16 var2);
Word32 sub_sh(Word32 L_var, Word16 var1, Word16 shift);
Word32 sub_sh16(Word32 L_var, Word16 var1);

/* Extended precision functions */

Word32 div_32(Word32 L_num, Word16 hi, Word16 lo);
Word32 L_comp(Word16 hi, Word16 lo);
void   L_extract(Word32 L_32, Word16 *hi, Word16 *lo);
Word32 mpy_mix(Word16 hi1, Word16 lo1, Word16 lo2);
Word32 mpy_32(Word16 hi1, Word16 lo1, Word16 hi2, Word16 lo2);


/* Mathematic functions  */

Word32 inv_sqrt(Word32 L_x);
void   Log2(Word32 L_x, Word16 *exponant, Word16 *fraction);
Word32 pow2(Word16 exponant, Word16 fraction);

/* General signal processing */

void   Autocorr(Word16 x[], Word16 p, Word16 r_h[], Word16 r_l[]);
void   Az_Lsp(Word16 a[], Word16 lsp[], Word16 old_lsp[]);
void   Back_Fil(Word16 x[], Word16 h[], Word16 y[], Word16 L);
Word16 Chebps(Word16 x, Word16 f[], Word16 n);
void   Convolve(Word16 x[], Word16 h[], Word16 y[], Word16 L);
void   Fac_Pond(Word16 gamma, Word16 fac[]);
void   Get_Lsp_Pol(Word16 *lsp, Word32 *f);
void   Int_Lpc4(Word16 lsp_old[], Word16 lsp_new[], Word16 a_4[]);
void   Lag_Window(Word16 p, Word16 r_h[], Word16 r_l[]);
void   Levin_32(Word16 Rh[], Word16 Rl[], Word16 A[]);
Word32 Lpc_Gain(Word16 a[]);
void   Lsp_Az(Word16 lsp[], Word16 a[]);
void   Pond_Ai(Word16 a[], Word16 fac[], Word16 a_exp[]);
void   Residu(Word16 a[], Word16 x[], Word16 y[], Word16 lg);
void   Syn_Filt(Word16 a[], Word16 x[], Word16 y[], Word16 lg, Word16 mem[],
                Word16 update);

/* Specific coder functions */

void   Init_Coder_Tetra(void);
void   Coder_Tetra(Word16 ana[], Word16 synth[]);
void   Cal_Rr2(Word16 h[], Word16 *rr);
void   Clsp_334(Word16 *lsp, Word16 *lsp_q, Word16 *indice);
Word16 D4i60_16(Word16 dn[], Word16 f[], Word16 h[], Word16 rr[][32],
                Word16 cod[], Word16 y[], Word16 *sign, Word16 *shift_code);
Word16 Ener_Qua(Word16 A[], Word16 prd_lt[], Word16 code[], Word16 L_subfr,
                Word16 *gain_pit, Word16 *gain_cod);
Word16 G_Code(Word16 xn2[], Word16 y2[], Word16 L_subfr);
Word16 G_Pitch(Word16 xn[], Word16 y1[], Word16 L_subfr);
void   Init_Pre_Process(void);
Word16 Lag_Max(Word16 signal[], Word16 sig_dec[], Word16 L_frame,
               Word16 lag_max, Word16 lag_min, Word16 *cor_max);
Word16 Pitch_Fr(Word16 exc[], Word16 xn[], Word16 h[], Word16 L_subfr,
                Word16 t0_min, Word16 t0_max, Word16 i_subfr,
		    Word16 *pit_frac);
Word16 Pitch_Ol_Dec(Word16 signal[], Word16 L_frame);
void   Pred_Lt(Word16 exc[], Word16 T0, Word16 frac, Word16 L_subfr);
void   Pre_Process(Word16 signal[], Word16 lg);
void   Prm2bits_Tetra(Word16 prm[], Word16 bits[]);

/* Specific decoder functions */

void   Init_Decod_Tetra(void);
void   Decod_Tetra(Word16 parm[], Word16 synth[]);
void   Bits2prm_Tetra(Word16 bits[], Word16 prm[]);
Word16 Dec_Ener(Word16 index, Word16 bfi, Word16 A[], Word16 prd_lt[],
	    Word16 code[], Word16 L_subfr, Word16 *gain_pit, Word16 *gain_cod);
void   D_D4i60(Word16 index,Word16 sign,Word16 shift, Word16 F[], 
	    Word16 cod[]);
void   D_Lsp334(Word16 indice[], Word16 lsp[], Word16 old_lsp[]);
void   Post_Process(Word16 signal[], Word16 lg);

#endif



/************************************************************************
*
*	DESCRIPTION		:     OPERATOR PROTOTYPES for TETRA codec
*
************************************************************************/

#ifndef TETRA_OP_H
#define TETRA_OP_H


/*-----------------------*
 * Constants and Globals *
 *-----------------------*/


extern Flag Overflow;
extern Flag Carry;

#define MAX_32 (Word32)0x7fffffff
#define MIN_32 (Word32)0x80000000

#define MAX_16 (Word16)0x7fff
#define MIN_16 (Word16)0x8000


/*-----------------------*
 * Operators prototypes  *
 *-----------------------*/

Word16 abs_s(Word16 var1);                /* Short abs,           1 */
Word16 add(Word16 var1, Word16 var2);     /* Short add,           1 */
Word16 div_s(Word16 var1, Word16 var2);   /* Short division,     18 */
Word16 extract_h(Word32 L_var1);          /* Extract high,        1 */
Word16 extract_l(Word32 L_var1);          /* Extract low,         1 */
Word16 mult(Word16 var1, Word16 var2);    /* Short mult,          1 */
Word16 mult_r(Word16 var1, Word16 var2);  /* Mult with round,     2 */
Word16 negate(Word16 var1);               /* Short negate,        1 */
Word16 norm_l(Word32 L_var1);             /* Long norm,          30 */
Word16 norm_s(Word16 var1);               /* Short norm,         15 */
Word16 round(Word32 L_var1);              /* Round,               1 */
Word16 shl(Word16 var1, Word16 var2);     /* Short shift left,    1 */
Word16 shr(Word16 var1, Word16 var2);     /* Short shift right,   1 */
Word16 sub(Word16 var1, Word16 var2);     /* Short sub,           1 */

Word32 L_abs(Word32 L_var1);              /* Long abs,            3 */
Word32 L_add(Word32 L_var1, Word32 L_var2);  /* Long add,         2 */
Word32 L_deposit_h(Word16 var1);          /* 16 bit var1 -> MSB   2 */
Word32 L_deposit_l(Word16 var1);          /* 16 bit var1 -> LSB,  2 */
Word32 L_mac(Word32 L_var3, Word16 var1, Word16 var2);  /* Mac,   1 */
Word32 L_mac0(Word32 L_var3, Word16 var1, Word16 var2); /* no shi 1 */
Word32 L_msu(Word32 L_var3, Word16 var1, Word16 var2);  /* Msu,   1 */
Word32 L_msu0(Word32 L_var3, Word16 var1, Word16 var2); /* no shi 1 */
Word32 L_mult(Word16 var1, Word16 var2);  /* Long mult,           1 */
Word32 L_mult0(Word16 var1, Word16 var2); /* Long mult no shift,  1 */
Word32 L_negate(Word32 L_var1);           /* Long negate,         2 */
Word32 L_shl(Word32 L_var1, Word16 var2); /* Long shift left,     2 */
Word32 L_shr(Word32 L_var1, Word16 var2); /* Long shift right,    2 */
Word32 L_shr_r(Word32 L_var1, Word16 var2);  /* L_shr with round, 3 */
Word32 L_sub(Word32 L_var1, Word32 L_var2);  /* Long sub,         2 */

#endif

