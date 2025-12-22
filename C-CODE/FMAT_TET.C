/************************************************************************
*
*	FILENAME		:	fmat_tet.c
*
*	DESCRIPTION		:	Library of mathematic functions used in the TETRA codec
*
************************************************************************
*
*	FUNCTIONS		:	- inv_sqrt()
*					- Log2()
*					- pow2()
*
************************************************************************
*
*	INCLUDED FILES	:	source.h
*
*					inv_sqrt.tab
*					log2.tab
*					pow2.tab
*
************************************************************************/

#include "source.h"

#include "inv_sqrt.tab"         /* Table for inv_sqrt() */
#include "log2.tab"             /* Table for Log2() */
#include "pow2.tab"             /* Table for pow2() */


/************************************************************************
*
*	Function Name : inv_sqrt
*
*	Purpose :
*
*		Compute 1/sqrt(L_x).
*		L_x is positive. The result is in Q30.
*
*	Complexity Weight : 56
*
*	Inputs :
*
*		L_x
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x0000 0000 <= L_x <= 0x7fff ffff.
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		L_y
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x0000 0000 <= L_y <= 0x3fff ffff.
*			L_y is a Q30 value (point between b30 and b29)
*
*	Algorithm :
*
*		The function 1/sqrt(L_x) is approximated by a table (tab_inv_sqrt)
*		and linear interpolation :
*
*			1 - Normalization of L_x
*			2 - If (30-exponant) is even then shift right once
*			3 - exponant = (30-exponant)/2  +1
*			4 - i = bit25-b31 of L_x,    16 <= i <= 63  ->because of normalization
*			5 - a = bit10-b24
*			6 - i -=16
*			7 - L_y = tab_inv_sqrt[i]<<16 - (tab_inv_sqrt[i] - tab_inv_sqrt[i+1]) * a * 2
*			8 - L_y >>= exponant
*
************************************************************************/

Word32 inv_sqrt(Word32 L_x)
{
  Word16 exp, i, a, tmp;
  Word32 L_y;

  if( L_x <= (Word32)0) return ( (Word32)0x3fffffff);


  exp = norm_l(L_x);
  L_x = L_shl(L_x, exp );		/* L_x is normalized */

  exp = sub( (Word16)30, exp );
  if( (exp & 1) == 0 )			/* If exponant even -> shift right */
      L_x = L_shr( L_x, (Word16)1 );

  exp = shr( exp, (Word16)1 );
  exp = add( exp, (Word16)1 );

  L_x = L_shr( L_x, (Word16)9 );
  i   = extract_h(L_x);			/* Extract b25-b31 */
  L_x = L_shr( L_x, (Word16)1 );
  a   = extract_l(L_x);			/* Extract b10-b24 */
  a   = a & (Word16)0x7fff;

  i   = sub( i, (Word16)16 );

  L_y = L_deposit_h(tab_inv_sqrt[i]);	/* tab_inv_sqrt[i] << 16 */
  tmp = sub(tab_inv_sqrt[i], tab_inv_sqrt[i+1]);
					    /* tab_inv_sqrt[i] - tab_inv_sqrt[i+1])*/
  L_y = L_msu(L_y, tmp, a);			/* L_y -=  tmp*a*2 */

  L_y = L_shr(L_y, exp);		/* denormalization */

  return(L_y);
}


/************************************************************************
*
*	Function Name : Log2
*
*	Purpose :
*
*		Compute Log2(L_x).
*		L_x is positive.
*
*	Complexity Weight : 48
*
*	Inputs :
*
*		L_x
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x0000 0000 <= L_x <= 0x7fff ffff.
*
*	Outputs :
*
*		exponant
*			Integer part of Log2()
*			16 bit  signed integer (Word16) whose value falls in the
*			range :   0 <= exponant <= 30
*
*		fraction
*			Fractional part of Log2()
*			16 bit signed integer (Word16) whose value falls in the
*			range : 0x0000 0000 <= fraction <= 0x7fff.
*			It's a Q15 value (point between b15 and b16).
*
*	Returned Value :
*
*		none
*
*	Algorithm :
*
*		The function Log2(L_x) is approximated by a table (tab_log2) 
*		and linear interpolation :
*
*			1 - Normalization of L_x
*			2 - exponant = 30-exponant
*			3 - i = bit25-b31 of L_x,    32 <= i <= 63  ->because of normalization
*			4 - a = bit10-b24
*			5 - i -=32
*			6 - fraction = tab_log2[i]<<16 - (tab_log2[i] - tab_log2[i+1]) * a * 2
*
************************************************************************/

void Log2(Word32 L_x, Word16 *exponant, Word16 *fraction)
{
  Word16 exp, i, a, tmp;
  Word32 L_y;

  if( L_x <= (Word32)0 )
  {
    *exponant = 0;
    *fraction = 0;
    return;
  }

  exp = norm_l(L_x);
  L_x = L_shl(L_x, exp );			/* L_x is normalized */
  
  *exponant = sub( (Word16)30, exp );

  L_x = L_shr( L_x, (Word16)9 );
  i   = extract_h(L_x);				/* Extract b25-b31 */
  L_x = L_shr( L_x, (Word16)1 );
  a   = extract_l(L_x);				/* Extract b10-b24 of fraction */
  a   = a & (Word16)0x7fff;

  i   = sub( i, (Word16)32 );

  L_y = L_deposit_h(tab_log2[i]);		/* tab_log2[i] << 16 */
  tmp = sub(tab_log2[i], tab_log2[i+1]);	/* tab_log2[i] - tab_log2[i+1] */
  L_y = L_msu(L_y, tmp, a);			/* L_y -= tmp*a*2 */

  *fraction = extract_h( L_y);

  return;
}


/************************************************************************
*
*	Function Name : pow2
*
*	Purpose :
*
*		L_x = pow(2.0, exponant.fraction).
*
*	Complexity Weight : 17
*
*	Inputs :
*
*		exponant
*			Integer part
*			16 bit  signed integer (Word16) whose value falls in the
*			range :   0 <= exponant <= 30
*
*		fraction
*			Fractional part
*			16 bit signed integer (Word16) whose value falls in the
*			range : 0x0000 0000 <= fraction <= 0x7fff.
*			It's a Q15 value (point between b15 and b16).
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		L_x
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x0000 0000 <= L_x <= 0x7fff ffff.
*
*	Algorithm :
*
*		The function pow2(L_x) is approximated by a table (tab_pow2)
*		and linear interpolation :
*
*			1 - i = bit11-b16 of fraction,   0 <= i <= 31
*			2 - a = bit0-b10  of fraction
*			3 - L_x = tab_pow2[i]<<16 - (tab_pow2[i] - tab_pow2[i+1]) * a * 2
*			4 - L_x = L_x >> (30-exponant)     (with rounding)
*
************************************************************************/

Word32 pow2(Word16 exponant, Word16 fraction)
{
  Word16 exp, i, a, tmp;
  Word32 L_x;

  L_x = L_deposit_l(fraction);
  L_x = L_shl( L_x, (Word16)6 );
  i   = extract_h(L_x);				/* Extract b10-b16 of fraction */
  L_x = L_shr( L_x, (Word16)1 );
  a   = extract_l(L_x);				/* Extract b0-b9   of fraction */
  a   = a & (Word16)0x7fff;


  L_x = L_deposit_h(tab_pow2[i]);		/* tab_pow2[i] << 16 */
  tmp = sub(tab_pow2[i], tab_pow2[i+1]);	/* tab_pow2[i] - tab_pow2[i+1] */
  L_x = L_msu(L_x, tmp, a);			/* L_x -= tmp*a*2  */

  exp = sub( (Word16)30, exponant );
  L_x = L_shr_r(L_x, exp);
  return(L_x);
}

