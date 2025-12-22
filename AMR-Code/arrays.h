/**************************************************************************
*
*	FILENAME				:	arrays.tab
*
*	DESCRIPTION			:	Arrays for speech channel coding and decoding
*
**************************************************************************/

/* ARRAYS FOR INITIALIZATION OF THE CHANNEL CODING */
/* Definition of the sensitivity classes : 3 classes */
extern Word16	TAB0[MAX_N0];
/* Class 0 */
extern Word16	TAB1[MAX_N1];
/* Class 1 */
extern Word16	TAB2[MAX_N2];
/* Class 2 */


extern Word16	Fs_TAB0[MAX_SpFrms_per_TDMFrm][MAX_N0];
/* Class 0 */
extern Word16	Fs_TAB1[MAX_SpFrms_per_TDMFrm][MAX_N1];
/* Class 1 */
extern Word16	Fs_TAB2[MAX_SpFrms_per_TDMFrm][MAX_N2];
/* Class 2 */

extern Word16	Fs_Fixed_Bit_TAB[MAX_SpFrms_per_TDMFrm][MAX_N0 + MAX_N1 + MAX_N2];
extern Word16	Fs_Fixed_Bit_List[MAX_SpFrms_per_TDMFrm * (MAX_N0 + MAX_N1 + MAX_N2)];

/* PUNCTURING CHARACTERISTICS: */
/* Puncturing Tables for the two protected classes (Class 1 and 2) */

extern Word16	A1[Period_pct*3];
/* Puncturing Table for Class 1 */

extern Word16	A2[Period_pct*3];
/* Puncturing Table for Class 2 */

extern Word16	Fs_A1[Period_pct*3];
/* In case of Frame Stealing */
/* Puncturing Table for Class 1 */

extern Word16	Fs_A2[Period_pct*3];
/* In case of Frame Stealing */
/* Puncturing Table for Class 2 */



/* BAD FRAME INDICATOR : CRC (Cyclic Redundant Check) */
/* Definition of the 8 CRC bits */

extern Word16	TAB_CRC1[MAX_SIZE_TAB_CRC1];
/* Ranks of the bits in Class2 protected by the First bit of the CRC */

extern Word16	TAB_CRC2[MAX_SIZE_TAB_CRC2];
/* Ranks of the bits in Class 2 protected by the Second bit of the CRC */

extern Word16	TAB_CRC3[MAX_SIZE_TAB_CRC3];
/* Ranks of the bits in Class 2 protected by the Third bit of the CRC */

extern Word16	TAB_CRC4[MAX_SIZE_TAB_CRC4];
/* Ranks of the bits in Class 2 protected by the Fourth bit of the CRC */

extern Word16	TAB_CRC5[MAX_SIZE_TAB_CRC5];
/* Ranks of the bits in Class 2 protected by the Fifth bit of the CRC */

extern Word16	TAB_CRC6[MAX_SIZE_TAB_CRC6];
/* Ranks of the bits in Class 2 protected by the Sixth bit of the CRC */

extern Word16	TAB_CRC7[MAX_SIZE_TAB_CRC7];
/* Ranks of the bits in Class 2 protected by the Seventh bit of the CRC */

extern Word16	TAB_CRC8[MAX_SIZE_TAB_CRC8];
/* Ranks of the bits in Class 2 protected by the Eighth bit of the CRC */




/* NOTHING MODIFIED BELOW HERE !!!! */



/* IN CASE OF FRAME STEALING :
   BAD FRAME INDICATOR : CRC (Cyclic Redundant Check)
   Definition of the 4 CRC bits
*/

extern Word16	Fs_TAB_CRC1[MAX_Fs_SIZE_TAB_CRC1];
/* Ranks of the bits in Class2 protected by the First bit of the CRC */

extern Word16	Fs_TAB_CRC2[MAX_Fs_SIZE_TAB_CRC2];
/* Ranks of the bits in Class 2 protected by the Second bit of the CRC */

extern Word16	Fs_TAB_CRC3[MAX_Fs_SIZE_TAB_CRC3];
/* Ranks of the bits in Class 2 protected by the Third bit of the CRC */

extern Word16	Fs_TAB_CRC4[MAX_Fs_SIZE_TAB_CRC4];
/* Ranks of the bits in Class 2 protected by the Fourth bit of the CRC */


extern Word16	Previous[(1 << (K - 1))][2];
extern Word16	Best_previous[(1 << (K - 1))][Decoding_delay];
extern Word16	T1[(1 << (K - 1))][2], T2[(1 << (K - 1))][2], T3[(1 << (K - 1))][2];
extern Word16	Score[(1 << (K - 1))];
extern Word16	Ex_score[(1 << (K - 1))];
extern Word16	Received[3];

extern Word16	Initialization;
extern Word16	Nber_Info_Bits;
extern Word16	Msb_bit;
extern Word16	M_1;
extern Word16	Min_value_allowed;
extern Word16	Max_value_allowed;
/* END GLOBAL VARIABLES ***********************************/

