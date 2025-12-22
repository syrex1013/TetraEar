/************************************************************************
*
*	FILENAME		:	fexp_tet.c
*
*	DESCRIPTION		:	Library of special functions for operations in
*					extended precision used in the TETRA speech codec
*
************************************************************************
*
*	FUNCTIONS		:	- L_comp()
*					- L_extract()
*					- mpy_mix()
*					- mpy_32()
*					- div_32()
*
************************************************************************
*
*	INCLUDED FILES	:	source.h
*
************************************************************************
*
*	COMMENTS		:	This subsection contains operations in double precision.
*					These operations are non standard double precision 
*					operations.
*
*					They are used where single precision is not enough but the 
*					full 32 bits precision is not necessary. For example, the 
*					function div_32() has a 24 bits precision.
*
*					The double precision numbers use a special representation :
*
*					L_32 = hi<<15 + lo
*
*					L_32 is a 32 bit integer with b30 == b31.
*					hi and lo are 16 bit signed integers.
*					As the low part also contains the sign, this allows fast
*					multiplication.
*
*					0xc000 0000 <= L_32 <= 0x3fff ffff.
*
*					In general, DPF is used to specify this special 
*					format.
*
************************************************************************/

#include "source.h"


/************************************************************************
*
*	Function Name : L_comp
*
*	Purpose :
*
*		Compose from two 16 bit DPF a normal 32 bit integer.
*		L_32 = hi<<15 + lo
*
*	Complexity Weight : 2
*
*	Inputs :
*
*		hi
*			msb
*
*		lo
*			lsb (with sign)
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		L_32
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0xc000 0000 <= L_32 <= 0x3fff ffff.
*
************************************************************************/

Word32 L_comp(Word16 hi, Word16 lo)
{
  return(add_sh( Load_sh( lo,(Word16)0 ), hi, (Word16)15 ));
}


/************************************************************************
*
*	Function Name : L_extract
*
*	Purpose :
*
*		Extract from a 31 bit integer two 16 bit DPF.
*
*	Complexity Weight : 5
*
*	Inputs :
*
*		L_32
*			32 bit long signed integer (Word32) with b30 == b31
*			whose value falls in the range : 0xc000 0000 <= L_32 <= 0x3fff ffff.
*
*	Outputs :
*
*		hi
*			b15 to b30 of L_32
*
*		lo
*			L_32 - hi<<15
*
*	Returned Value :
*
*		none
*
************************************************************************/

void L_extract(Word32 L_32, Word16 *hi, Word16 *lo)
{
  *hi  = extract_h( L_shl( L_32,(Word16)1 ) );
  *lo  = extract_l( sub_sh( L_32, *hi, (Word16)15 ) );
  return;
}


/************************************************************************
*
*	Function Name : mpy_mix
*
*	Purpose :
*
*		Multiply a 16 bit integer by a 32 bit (DPF). 
*		The result is divided by 2**16
*		L_32 = hi1*lo2 + (lo1*lo2)>>15
*
*	Complexity Weight : 4
*
*	Inputs :
*
*		hi1
*			hi part of 32 bit number
*
*		lo1
*			lo part of 32 bit number
*
*		lo2
*			16 bit number
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		L_var_out
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x0000 0000 <= L_var_out <= 0x7fff ffff.
*
************************************************************************/

Word32 mpy_mix(Word16 hi1, Word16 lo1, Word16 lo2)
{
  Word16 p1;
  Word32 L_32;

  p1   = extract_h(L_mult0(lo1, lo2));
  L_32 = L_mult0(hi1,lo2 );

  return(add_sh( L_32, p1, (Word16)1 ));
}


/************************************************************************
*
*	Function Name : mpy_32
*
*	Purpose :
*
*		Multiply two 32 bit integers (DPF). The result is divided by 2**32
*		L_32 = hi1*hi2 + (hi1*lo2)>>15 + (lo1*hi2)>>15)
*
*	Complexity Weight : 7
*
*	Inputs :
*
*		hi1
*			hi part of first number
*
*		lo1
*			lo part of first number
*
*		hi2
*			hi part of second number
*
*		lo2
*			lo part of second number
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		L_var_out
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x0000 0000 <= L_var_out <= 0x7fff ffff.
*
*************************************************************************/

Word32 mpy_32(Word16 hi1, Word16 lo1, Word16 hi2, Word16 lo2)
{
  Word16 p1, p2;
  Word32 L_32;

  p1   = extract_h(L_mult0(hi1, lo2));
  p2   = extract_h(L_mult0(lo1, hi2));
  L_32 = L_mult0(hi1, hi2);
  L_32 = add_sh( L_32, p1, (Word16)1 );

  return(add_sh( L_32, p2, (Word16)1 ));
}


/************************************************************************
*
*	Function Name : div_32
*
*	Purpose :
*
*		Fractionnal integer division of two 32 bit numbers.
*		L_num / L_denom
*		L_num and L_denom must be positive and L_num < L_denom
*		L_denom = denom_hi<<15 + denom_lo
*		denom_hi is a normalized number
*		The result is in Q30
*
*	Complexity Weight : 52
*
*	Inputs :
*
*		L_num
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x0000 0000 <= L_num <= L_denom.
*
*		(L_denom = denom_hi<<15 + denom_lo)
*
*		denom_hi
*			16 bit normalized integer whose value falls in the
*			range : 0x4000000 < hi < 0x7fff ffff.
*
*		denom_lo
*			16 bit positive integer whose value falls in the
*			range : 0 < lo < 0x7fff ffff.
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		L_div
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x0000 0000 <= L_div <= 0x3fff ffff.
*			L_div is a Q30 value (point between b30 and b29)
*
*	Algorithm :
*
*		 - find = 1/L_denom
*			First approximation: approx = 1 / denom_hi
*			1/L_denom = approx * (2.0 - L_denom * approx )
*		-  result = L_num * (1/L_denom)
*
************************************************************************/

Word32 div_32(Word32 L_num, Word16 denom_hi, Word16 denom_lo)
{
  Word16 approx, hi, lo, n_hi, n_lo;
  Word32 t0;


  /* First approximation: 1 / L_denom = 1/denom_hi */

  approx = div_s( (Word16)0x3fff, denom_hi);	/* result in Q15 */

 
 
/* 1/L_denom = approx * (2.0 - L_denom * approx) */

  t0 = mpy_mix(denom_hi, denom_lo, approx);	/* result in Q29 */

  t0 = L_sub( (Word32)0x40000000, t0);		/* result in Q29 */

  L_extract(t0, &hi, &lo);

  t0 = mpy_mix(hi, lo, approx);			/* = 1/L_denom in Q28 */

  /* L_num * (1/L_denom) */

  L_extract(t0, &hi, &lo);
  L_extract(L_num, &n_hi, &n_lo);
  t0 = mpy_32(n_hi, n_lo, hi, lo);

  return( L_shl( t0,(Word16)2) );			/* From Q28 to Q30 */
}

