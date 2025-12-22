/************************************************************************
*
*	FILENAME		:		channel.h
*
*	DESCRIPTION	:		DEFINITIONS
*
*						FUNCTION PROTOTYPES for the TETRA
*						speech channel coder and 
*						speech channel decoder
*
*						OPERATOR PROTOTYPES for TETRA codec
*
************************************************************************/

/***********************************************************************
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
*						speech channel coder
*
************************************************************************/

#ifndef SUB_CC_H
#define SUB_CC_H


#include <stdio.h>

Word16	Build_Crc(Word16 FS_Flag, Word16 Input_Frame[]);
Word16	Build_Sensitivity_Classes(Word16 FS_Flag, Word16 Input_Frame[], 			Word16 Output_Frame[]);
Word16	Combination(Word16 A, Word16 B);
void		Channel_Encoding(short first_pass, Word16 Frame_Stealing,
			Word16 Input_Frame[], Word16 Output_Frame[]);
void		Init_Rcpc_Coding(Word16 FS_Flag, Word16 Input_Frame[]);
Word16	Interleaving_Signalling(Word16 Input_Frame[],
			Word16 Output_frame[]);
Word16	Interleaving_Speech(Word16 Input_Frame[], Word16 Output_frame[]);
void		Rcpc_Coding(Word16 FS_Flag, Word16 Input_Frame[],
			Word16 Output_Frame[]);
void		Transform_Class_0(Word16 FS_Flag, Word16 Input_Frame[]);
short		Write_Tetra_File (FILE *fout, short *array);

#endif



/************************************************************************
*
*	DESCRIPTION		:	FUNCTION PROTOTYPES for the TETRA
*						speech channel decoder
*
************************************************************************/

#ifndef SUB_CD_H
#define SUB_CD_H


Word16	Bfi(Word16 FS_Flag, Word16 Input_Frame[]);
Word16	Channel_Decoding(short first_pass, Word16 Frame_Stealing,
			Word16 Input_Frame[], Word16 Output_Frame[]);
Word16	Combination(Word16 A, Word16 B);
Word16	Desinterleaving_Signalling(Word16 Input_Frame[],
			Word16 Output_frame[]);
Word16	Desinterleaving_Speech(Word16 Input_Frame[],
			Word16 Output_frame[]);
void		Init_Rcpc_Decoding(void);
void		Rcpc_Decoding(Word16 FS_Flag, Word16 Input_Frame[],
			Word16 Output_Frame[]);
short		Read_Tetra_File (FILE *fin, short *array);
Word16	Unbuild_Sensitivity_Classes(Word16 FS_Flag, Word16 Input_Frame[],
			Word16 Output_Frame[]);
Word16	Untransform_Class_0(Word16 FS_Flag, Word16 Input_Frame[]);

#endif


/************************************************************************
*
*	DESCRIPTION		:	OPERATOR PROTOTYPES for TETRA codec
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

